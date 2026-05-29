import os
import logging
import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode

from app.models.models import User
from app.database.connection import AsyncSessionLocal
from sqlalchemy import select

from app.tools.campus_tools import (
    get_campus_events,
    get_course_reminders,
    get_weather_forecast,
)
from app.services.llm_service import LLMService, LLMServiceError
from app.utils.telegram_formatter import build_newsletter_message, escape_markdown_v2

logger = logging.getLogger(__name__)

# Conversation states for registration (/start)
ASK_COLLEGE, ASK_PROGRAM = range(2)

# Load Jinja environment
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

# Initialize LLM Service
llm_service = LLMService()

def parse_prompt_template(rendered_text: str) -> tuple[str, str]:
    """
    Parses a rendered Jinja template containing System: and User: labels
    into separate system and user prompts for the LLM.
    """
    default_system = "You are a helpful college newsletter assistant."
    if "System:" in rendered_text and "User:" in rendered_text:
        try:
            parts = rendered_text.split("User:")
            system_part = parts[0].replace("System:", "").strip()
            user_part = parts[1].strip()
            return system_part, user_part
        except Exception as e:
            logger.warning(f"Error parsing system/user prompt tags: {e}. Using fallback structure.")
            
    return default_system, rendered_text

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Initiates the registration conversation handler.
    Asks the user for their college name.
    """
    logger.info(f"User {update.effective_user.id} triggered /start")
    await update.message.reply_text(
        "👋 Welcome to the Personalized College Newsletter Bot!\n\n"
        "To get started, please tell me the name of your College or School "
        "(e.g., 'School of Engineering' or 'College of Arts and Sciences'):"
    )
    return ASK_COLLEGE

async def college_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Stores the college response and asks the user for their academic program.
    """
    college_name = update.message.text.strip()
    if not college_name:
        await update.message.reply_text("Please enter a valid college name:")
        return ASK_COLLEGE

    context.user_data["college"] = college_name
    logger.info(f"User {update.effective_user.id} entered college: {college_name}")
    
    await update.message.reply_text(
        f"Great! You entered: *{college_name}*.\n\n"
        f"Now, please enter your specific academic Program or Major "
        f"(e.g., 'Computer Science' or 'Data Science'):",
        parse_mode=ParseMode.MARKDOWN
    )
    return ASK_PROGRAM

async def program_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Stores the program response, saves user data to the database, and ends registration.
    """
    program_name = update.message.text.strip()
    if not program_name:
        await update.message.reply_text("Please enter a valid program name:")
        return ASK_PROGRAM

    college_name = context.user_data.get("college")
    chat_id = update.effective_user.id

    logger.info(f"User {chat_id} entered program: {program_name}. Saving to database...")

    try:
        async with AsyncSessionLocal() as session:
            # Check if user already exists
            stmt = select(User).where(User.chat_id == chat_id)
            result = await session.execute(stmt)
            user = result.scalars().first()

            if user:
                user.college = college_name
                user.program = program_name
                user.is_active = True
                logger.info(f"Updated existing user profile for chat_id={chat_id}")
            else:
                user = User(
                    chat_id=chat_id,
                    college=college_name,
                    program=program_name,
                    is_active=True
                )
                session.add(user)
                logger.info(f"Created new user profile for chat_id={chat_id}")

            await session.commit()

        await update.message.reply_text(
            "🎉 *Registration Complete!*\n\n"
            f"📍 *College:* {college_name}\n"
            f"📚 *Program:* {program_name}\n\n"
            "You are now subscribed to receive weekly newsletters. "
            "You can trigger an on-demand newsletter at any time using /newsletter.",
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        logger.error(f"Error during registration database write: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ An error occurred while saving your profile. Please try running /start again."
        )

    return ConversationHandler.END

async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancels the registration conversation.
    """
    logger.info(f"User {update.effective_user.id} cancelled registration")
    await update.message.reply_text(
        "Registration cancelled. You can register anytime using the /start command."
    )
    return ConversationHandler.END

async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Sets is_active=False for the user. Does not delete records.
    """
    chat_id = update.effective_user.id
    logger.info(f"User {chat_id} triggered /unsubscribe")

    try:
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.chat_id == chat_id)
            result = await session.execute(stmt)
            user = result.scalars().first()

            if user:
                if not user.is_active:
                    await update.message.reply_text("You are already unsubscribed.")
                else:
                    user.is_active = False
                    await session.commit()
                    logger.info(f"Unsubscribed user chat_id={chat_id}")
                    await update.message.reply_text(
                        "😔 You have successfully unsubscribed. You will no longer receive weekly newsletters. "
                        "You can subscribe again at any time by running /start."
                    )
            else:
                await update.message.reply_text(
                    "You are not currently registered. Type /start to register."
                )
    except Exception as e:
        logger.error(f"Error during unsubscribe database write: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ An error occurred during unsubscribe. Please try again later."
        )

async def generate_newsletter_content(user: User) -> str:
    """
    Helper function to orchestrate the entire newsletter generation workflow:
    1. Fetch events, reminders, weather
    2. Render Jinja templates
    3. Generate sections with Ollama (or use graceful plaintext fallbacks)
    4. Format and combine them using MarkdownV2 syntax
    """
    # Step 1-3: Fetch data
    events = await get_campus_events()
    reminders = await get_course_reminders(user.program)
    
    # Try to resolve weather for user's college first
    default_loc = os.getenv("WEATHER_DEFAULT_LOCATION", "New York,US")
    weather = await get_weather_forecast(user.college)
    if weather.get("status") == "mocked" and user.college != default_loc:
        # If weather for college was not resolved (returned mock), try default location
        weather = await get_weather_forecast(default_loc)

    # Step 4: Render Jinja templates & Step 5-6: Send to Ollama & Generate Sections
    
    # --- Generate Events Section ---
    try:
        events_tmpl = jinja_env.get_template("events.j2")
        events_prompt_rendered = events_tmpl.render(events=events)
        sys_p, usr_p = parse_prompt_template(events_prompt_rendered)
        events_section = await llm_service.generate_response(sys_p, usr_p)
    except Exception as e:
        logger.warning(f"Ollama events section generation failed: {e}. Using fallback formatting.")
        events_section = build_events_fallback(events)

    # --- Generate Course Reminders Section ---
    try:
        courses_tmpl = jinja_env.get_template("courses.j2")
        courses_prompt_rendered = courses_tmpl.render(courses=reminders)
        sys_p, usr_p = parse_prompt_template(courses_prompt_rendered)
        courses_section = await llm_service.generate_response(sys_p, usr_p)
    except Exception as e:
        logger.warning(f"Ollama courses section generation failed: {e}. Using fallback formatting.")
        courses_section = build_courses_fallback(reminders)

    # --- Generate Weather Section ---
    try:
        weather_tmpl = jinja_env.get_template("weather.j2")
        weather_prompt_rendered = weather_tmpl.render(weather=weather, location=weather.get("location"))
        sys_p, usr_p = parse_prompt_template(weather_prompt_rendered)
        weather_section = await llm_service.generate_response(sys_p, usr_p)
    except Exception as e:
        logger.warning(f"Ollama weather section generation failed: {e}. Using fallback formatting.")
        weather_section = build_weather_fallback(weather)

    # Step 7-8: Combine sections and format MarkdownV2
    message = build_newsletter_message(events_section, courses_section, weather_section)
    return message

async def newsletter_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    On-demand newsletter generation command.
    Checks if user is registered and active, then generates and sends the newsletter.
    """
    chat_id = update.effective_user.id
    logger.info(f"User {chat_id} requested newsletter on-demand.")

    # Find the user
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.chat_id == chat_id)
        result = await session.execute(stmt)
        user = result.scalars().first()

    if not user or not user.is_active:
        await update.message.reply_text(
            "⚠️ You must be registered and active to receive a newsletter.\n"
            "Please run /start to register."
        )
        return

    # Send typing / progress indicator since newsletter generation takes time
    progress_msg = await update.message.reply_text(
        "⏳ *Generating your personalized newsletter...*\n"
        "_Querying databases, fetching weather, and styling with AI._",
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        message = await generate_newsletter_content(user)
        
        # Send the final newsletter
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        # Delete the progress message
        await progress_msg.delete()
        logger.info(f"Successfully sent on-demand newsletter to chat_id={chat_id}")
        
    except Exception as e:
        logger.error(f"Failed to generate/send newsletter for user {chat_id}: {e}", exc_info=True)
        await progress_msg.edit_text(
            "⚠️ Sorry, an error occurred while generating your newsletter. Please try again later."
        )

# --- Fallback Formatting Helpers (No-LLM mode) ---

def build_events_fallback(events: list[dict]) -> str:
    """Creates a basic bulleted list of events if LLM fails."""
    if not events:
        return "No upcoming events scheduled for this week."
    
    lines = []
    for e in events:
        # Parse ISO date string
        dt_str = e["event_date"]
        try:
            dt = datetime.datetime.fromisoformat(dt_str)
            date_formatted = dt.strftime("%b %d, %I:%M %p")
        except Exception:
            date_formatted = dt_str
            
        lines.append(f"• *{e['name']}* \\({date_formatted}\\)\n  {e['description']}")
    return "\n".join(lines)

def build_courses_fallback(courses: list[dict]) -> str:
    """Creates a basic list of course reminders if LLM fails."""
    if not courses:
        return "There are no upcoming course reminders or deadlines for your program."
        
    lines = []
    for c in courses:
        dt_str = c["due_date"]
        try:
            dt = datetime.datetime.fromisoformat(dt_str)
            date_formatted = dt.strftime("%A, %b %d")
        except Exception:
            date_formatted = dt_str
            
        lines.append(f"• *{c['name']}*: {c['reminder']} \\(Due: {date_formatted}\\)")
    lines.append("\nKeep up the great work!")
    return "\n".join(lines)

def build_weather_fallback(weather: dict) -> str:
    """Creates a simple weather summary paragraph if LLM fails."""
    loc = weather.get("location", "Unknown Location")
    temp = weather.get("temp", "--")
    desc = weather.get("description", "Unknown")
    feels = weather.get("feels_like", "--")
    
    return (
        f"Currently in {loc}: {temp}°C, feels like {feels}°C with {desc.lower()}.\n"
        f"Stay prepared and plan your week accordingly!"
    )

def get_bot_conversation_handler() -> ConversationHandler:
    """
    Returns the registration ConversationHandler.
    """
    return ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            ASK_COLLEGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, college_response)
            ],
            ASK_PROGRAM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, program_response)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_registration)],
    )

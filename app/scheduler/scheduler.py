import logging
from sqlalchemy import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from telegram.constants import ParseMode

from app.models.models import User
from app.database.connection import AsyncSessionLocal
from app.bot.handlers import generate_newsletter_content

logger = logging.getLogger(__name__)

async def send_weekly_newsletters_job(bot: Bot) -> None:
    """
    Weekly newsletter job.
    Fetches all active users from the database, generates their personalized
    newsletters, and sends them via Telegram.
    """
    logger.info("Starting scheduled weekly newsletter delivery...")
    
    # Fetch active users
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.is_active == True)
            result = await session.execute(stmt)
            active_users = result.scalars().all()
            
        logger.info(f"Found {len(active_users)} active subscribers for newsletter.")
    except Exception as e:
        logger.error(f"Failed to fetch active users for scheduler: {e}", exc_info=True)
        return

    # Deliver to each user
    success_count = 0
    failure_count = 0

    for user in active_users:
        try:
            logger.info(f"Generating weekly newsletter for user chat_id={user.chat_id} ({user.program})")
            # Generate the newsletter text (includes Ollama & templates call)
            message = await generate_newsletter_content(user)
            
            # Send via Telegram bot client
            await bot.send_message(
                chat_id=user.chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            success_count += 1
            logger.info(f"Successfully sent weekly newsletter to chat_id={user.chat_id}")
            
        except Exception as e:
            failure_count += 1
            logger.error(
                f"Failed to send weekly newsletter to user chat_id={user.chat_id}: {e}", 
                exc_info=True
            )
            # We continue processing the remaining users even if one fails

    logger.info(
        f"Weekly newsletter delivery completed. "
        f"Success: {success_count}, Failures: {failure_count}."
    )

def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """
    Creates and starts the AsyncIOScheduler.
    Schedules the newsletter job to run weekly (every Monday at 9:00 AM).
    """
    scheduler = AsyncIOScheduler()
    
    # Schedule weekly newsletter delivery
    # Default is Monday at 09:00 AM, but can be configured if needed.
    scheduler.add_job(
        send_weekly_newsletters_job,
        trigger=CronTrigger(day_of_week="mon", hour=9, minute=0),
        args=[bot],
        id="weekly_newsletter",
        replace_existing=True
    )
    
    logger.info("Weekly newsletter scheduled: Every Monday at 9:00 AM.")
    scheduler.start()
    logger.info("Scheduler started successfully.")
    
    return scheduler

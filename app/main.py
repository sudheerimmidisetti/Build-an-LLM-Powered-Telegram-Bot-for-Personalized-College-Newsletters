import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging to console
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

from app.database.connection import init_db, AsyncSessionLocal
from data.seed import seed_database
from app.api.routes import router as mcp_router
from app.bot.handlers import (
    get_bot_conversation_handler,
    unsubscribe_command,
    newsletter_command
)
from app.scheduler.scheduler import setup_scheduler

from telegram.ext import ApplicationBuilder, CommandHandler

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the lifecycle of the FastAPI application.
    On startup: Initializes DB tables, seeds them, starts Telegram Bot async polling, and starts the scheduler.
    On shutdown: Stops Telegram Bot async polling and shuts down the scheduler.
    """
    logger.info("Initializing application services...")
    
    # 1. Database Setup & Seeding
    try:
        await init_db()
        async with AsyncSessionLocal() as session:
            await seed_database(session)
    except Exception as e:
        logger.critical(f"Database initialization or seeding failed: {e}", exc_info=True)
        # We don't crash the server, but log it heavily

    # 2. Telegram Bot Startup
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    bot_app = None
    scheduler = None
    
    if not bot_token:
        logger.warning(
            "TELEGRAM_BOT_TOKEN environment variable is missing. "
            "Telegram bot is disabled, but FastAPI web server is running."
        )
    else:
        try:
            logger.info("Starting Telegram Bot...")
            bot_app = ApplicationBuilder().token(bot_token).build()
            
            # Register Bot Command Handlers
            bot_app.add_handler(get_bot_conversation_handler())
            bot_app.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
            bot_app.add_handler(CommandHandler("newsletter", newsletter_command))
            
            # Initialize and start polling
            await bot_app.initialize()
            await bot_app.start()
            await bot_app.updater.start_polling()
            logger.info("Telegram Bot is running in polling mode.")
            
            # 3. Setup Scheduler
            logger.info("Starting Weekly Newsletter Scheduler...")
            scheduler = setup_scheduler(bot_app.bot)
            
            # Save references to application state for cleanup
            app.state.bot_app = bot_app
            app.state.scheduler = scheduler
        except Exception as e:
            logger.error(f"Failed to start Telegram Bot or Scheduler: {e}", exc_info=True)

    yield

    # Shutdown logic
    logger.info("Shutting down application services...")
    if bot_app:
        try:
            logger.info("Stopping Telegram Bot polling...")
            await bot_app.updater.stop()
            await bot_app.stop()
            await bot_app.shutdown()
            logger.info("Telegram Bot stopped successfully.")
        except Exception as e:
            logger.error(f"Error while stopping Telegram Bot: {e}")

    if scheduler:
        try:
            logger.info("Shutting down Scheduler...")
            scheduler.shutdown()
            logger.info("Scheduler shut down successfully.")
        except Exception as e:
            logger.error(f"Error while shutting down Scheduler: {e}")

# Initialize FastAPI App
app = FastAPI(
    title="LLM-Powered College Newsletter Service",
    description="FastAPI backend and Telegram Bot evaluator service.",
    version="1.0.0",
    lifespan=lifespan
)

# Register routes
app.include_router(mcp_router, tags=["MCP Tools"])

@app.get("/healthz")
async def health_check():
    """Simple API health check endpoint."""
    return {"status": "ok", "service": "newsletter-bot"}

if __name__ == "__main__":
    # Get port and host from env, run Uvicorn
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    logger.info(f"Starting server on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)

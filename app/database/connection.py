import os
import logging
from pathlib import Path
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.models.models import Base

logger = logging.getLogger(__name__)

# Fetch database URL from environment variables, fallback to sqlite+aiosqlite inside data/
database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/newsletter.db")

# Force using aiosqlite for SQLite to support async operations
if database_url.startswith("sqlite://"):
    database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)

# Ensure database directory exists
if "sqlite" in database_url:
    # Split scheme from the path portion
    parts = database_url.split("sqlite+aiosqlite://")
    if len(parts) > 1:
        db_file_path = parts[-1].lstrip("/")
        if db_file_path and not db_file_path.startswith(":memory:"):
            # Path can be absolute or relative
            db_dir = Path(db_file_path).parent
            try:
                db_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Database directory verified at: {db_dir.resolve()}")
            except Exception as e:
                logger.error(f"Failed to create database directory {db_dir}: {e}")

# Create async engine. 
# We use connect_args={"check_same_thread": False} for SQLite as it allows multi-threading
connect_args = {}
if "sqlite" in database_url:
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    database_url,
    connect_args=connect_args,
    echo=False,  # Set to True for debugging SQL queries if needed
    future=True
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection helper to yield database sessions.
    Cleans up the session automatically.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db() -> None:
    """
    Initializes the database by creating all missing tables.
    """
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized successfully.")

import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass

class User(Base):
    """
    Represents a Telegram user registered to receive newsletters.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    college: Mapped[str] = mapped_column(String, nullable=False)
    program: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<User chat_id={self.chat_id} college={self.college} program={self.program} active={self.is_active}>"

class Event(Base):
    """
    Represents a campus event.
    """
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    event_date: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:
        return f"<Event name={self.name} date={self.event_date}>"

class Course(Base):
    """
    Represents a course reminder/deadline.
    Note: The 'program' column is added to map reminders to specific user programs.
    """
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    program: Mapped[str] = mapped_column(String, nullable=False, index=True)
    reminder: Mapped[str] = mapped_column(String, nullable=False)
    due_date: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:
        return f"<Course name={self.name} program={self.program} due={self.due_date}>"

import datetime
import logging
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Event, Course

logger = logging.getLogger(__name__)

# Realistic data using relative dates to ensure they remain "upcoming" whenever tested
def get_seed_events() -> list[Event]:
    now = datetime.datetime.now()
    return [
        Event(
            name="AI & LLM Hackathon 2026",
            description="Collaborate with peers to build innovative AI applications. Cash prizes up to $5,000!",
            event_date=now + datetime.timedelta(days=2, hours=10)
        ),
        Event(
            name="Campus Spring Career Fair",
            description="Meet representatives from over 100 top companies for internships and full-time jobs.",
            event_date=now + datetime.timedelta(days=3, hours=9)
        ),
        Event(
            name="Quantum Computing Guest Lecture",
            description="Dr. Evelyn Shaw from MIT discusses the future of Quantum Entanglement and Cryptography.",
            event_date=now + datetime.timedelta(days=1, hours=14)
        ),
        Event(
            name="College Championship Football Game",
            description="The annual homecoming game against state rivals. Tailgating starts at 11:00 AM.",
            event_date=now + datetime.timedelta(days=5, hours=13)
        ),
        Event(
            name="Annual Campus Music Festival",
            description="Live outdoor concert featuring student bands, local artists, food trucks, and games.",
            event_date=now + datetime.timedelta(days=6, hours=17)
        ),
        Event(
            name="Undergraduate Research Symposium",
            description="Students present their poster boards and research findings to faculty and peers.",
            event_date=now + datetime.timedelta(days=7, hours=10)
        ),
        Event(
            name="Startup Pitch Competition",
            description="Pitch your venture idea to angel investors and win equity-free seed funding.",
            event_date=now + datetime.timedelta(days=4, hours=16)
        ),
        Event(
            name="Community Green Up Day",
            description="Volunteers gather to plant trees, clean gardens, and beautify the university grounds.",
            event_date=now + datetime.timedelta(days=2, hours=8)
        ),
        Event(
            name="Pre-Exams Yoga & Wellness Session",
            description="Free guided meditation, breathing exercise, and yoga to relieve midterm/final stress.",
            event_date=now + datetime.timedelta(days=4, hours=17)
        ),
        Event(
            name="Alumni Dinner & Panel Discussion",
            description="Network with distinguished alumni working in tech, finance, and humanities.",
            event_date=now + datetime.timedelta(days=8, hours=18)
        )
    ]

def get_seed_courses() -> list[Course]:
    now = datetime.datetime.now()
    return [
        Course(
            name="CS 101: Introduction to Python",
            program="Computer Science",
            reminder="Complete Assignment 4: Loops and File I/O operations.",
            due_date=now + datetime.timedelta(days=2, hours=23, minutes=59)
        ),
        Course(
            name="CS 202: Data Structures & Algorithms",
            program="Computer Science",
            reminder="Submit Project 1: Implement AVL Trees and perform complexity analysis.",
            due_date=now + datetime.timedelta(days=4, hours=23, minutes=59)
        ),
        Course(
            name="DS 301: Machine Learning Models",
            program="Data Science",
            reminder="Complete homework assignment on Gradient Descent optimization and Linear Regression.",
            due_date=now + datetime.timedelta(days=3, hours=23, minutes=59)
        ),
        Course(
            name="CS 404: Operating Systems",
            program="Computer Science",
            reminder="Lab 2: Multithreading and mutex synchronization due. Submit code and write-up.",
            due_date=now + datetime.timedelta(days=5, hours=23, minutes=59)
        ),
        Course(
            name="MATH 201: Linear Algebra",
            program="Computer Science",
            reminder="Complete weekly quiz on Eigenvalues, Eigenvectors, and Matrix Diagonalization.",
            due_date=now + datetime.timedelta(days=1, hours=23, minutes=59)
        ),
        Course(
            name="DS 102: Data Visualization Tools",
            program="Data Science",
            reminder="Submit your interactive dashboard designed in Tableau or using Plotly Dash.",
            due_date=now + datetime.timedelta(days=6, hours=23, minutes=59)
        ),
        Course(
            name="CS 305: Relational Database Systems",
            program="Computer Science",
            reminder="SQL Query Optimization lab due. Analyze execution plans for given indexes.",
            due_date=now + datetime.timedelta(days=7, hours=23, minutes=59)
        ),
        Course(
            name="DS 402: Deep Learning",
            program="Data Science",
            reminder="Submit project proposal outlining your CNN architecture and selected dataset.",
            due_date=now + datetime.timedelta(days=8, hours=23, minutes=59)
        ),
        Course(
            name="ENG 101: Academic Composition",
            program="Liberal Arts",
            reminder="Submit the final draft of your 1500-word persuasive essay on ethical technology.",
            due_date=now + datetime.timedelta(days=3, hours=23, minutes=59)
        ),
        Course(
            name="BUS 201: Principles of Finance",
            program="Business Administration",
            reminder="Analyze case study on capital budgeting decisions for multinational corporations.",
            due_date=now + datetime.timedelta(days=5, hours=23, minutes=59)
        ),
        Course(
            name="MATH 201: Linear Algebra",
            program="Data Science",
            reminder="Complete weekly quiz on Eigenvalues, Eigenvectors, and Matrix Diagonalization.",
            due_date=now + datetime.timedelta(days=1, hours=23, minutes=59)
        )
    ]

async def seed_database(session: AsyncSession) -> None:
    """
    Checks if events and courses are already seeded. If not, seeds them.
    """
    # Check if events table has records
    event_check = await session.execute(select(Event).limit(1))
    events_exist = event_check.scalars().first() is not None

    # Check if courses table has records
    course_check = await session.execute(select(Course).limit(1))
    courses_exist = course_check.scalars().first() is not None

    if not events_exist:
        logger.info("Seeding events table...")
        events = get_seed_events()
        session.add_all(events)
    else:
        logger.info("Events table already contains records. Skipping event seeding.")

    if not courses_exist:
        logger.info("Seeding courses table...")
        courses = get_seed_courses()
        session.add_all(courses)
    else:
        logger.info("Courses table already contains records. Skipping course seeding.")

    if not events_exist or not courses_exist:
        await session.commit()
        logger.info("Seeding completed successfully.")
    else:
        logger.info("Database already seeded.")

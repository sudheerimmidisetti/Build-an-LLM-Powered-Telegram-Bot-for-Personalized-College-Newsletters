import os
import logging
import datetime
import httpx
from typing import Any
from sqlalchemy import select
from app.database.connection import AsyncSessionLocal
from app.models.models import Event, Course

logger = logging.getLogger(__name__)

async def get_campus_events() -> list[dict[str, Any]]:
    """
    Fetches upcoming campus events scheduled for today or in the future.
    Returns a list of structured event records as dictionaries.
    """
    logger.info("Fetching campus events from database...")
    now = datetime.datetime.now()
    async with AsyncSessionLocal() as session:
        # Fetch events occurring from today onwards, ordered by date
        stmt = select(Event).where(Event.event_date >= now).order_by(Event.event_date)
        result = await session.execute(stmt)
        events = result.scalars().all()
        
        event_list = []
        for e in events:
            event_list.append({
                "id": e.id,
                "name": e.name,
                "description": e.description,
                "event_date": e.event_date.isoformat()
            })
        
        logger.info(f"Successfully fetched {len(event_list)} upcoming events.")
        return event_list

async def get_course_reminders(program: str) -> list[dict[str, Any]]:
    """
    Fetches upcoming course reminders matching a specific academic program.
    Returns a list of structured course reminder records as dictionaries.
    """
    logger.info(f"Fetching course reminders for program: {program}")
    now = datetime.datetime.now()
    async with AsyncSessionLocal() as session:
        # Fetch reminders for the program that are due in the future, ordered by due date
        stmt = select(Course).where(
            Course.program.icontains(program),
            Course.due_date >= now
        ).order_by(Course.due_date)
        
        result = await session.execute(stmt)
        courses = result.scalars().all()
        
        course_list = []
        for c in courses:
            course_list.append({
                "id": c.id,
                "name": c.name,
                "program": c.program,
                "reminder": c.reminder,
                "due_date": c.due_date.isoformat()
            })
            
        logger.info(f"Successfully fetched {len(course_list)} reminders for program '{program}'.")
        return course_list

async def get_weather_forecast(location: str) -> dict[str, Any]:
    """
    Fetches current weather and basic outlook for the given location using OpenWeatherMap.
    Falls back to mock data if the API key is not configured or if the request fails.
    """
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key:
        logger.warning("OPENWEATHERMAP_API_KEY environment variable is not set. Using mock weather data.")
        return get_mock_weather(location)
        
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": location,
        "appid": api_key,
        "units": "metric"
    }
    
    try:
        logger.info(f"Requesting weather forecast from OpenWeatherMap for location: {location}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                weather_data = {
                    "location": data.get("name", location),
                    "temp": data["main"]["temp"],
                    "feels_like": data["main"]["feels_like"],
                    "description": data["weather"][0]["description"].capitalize(),
                    "humidity": data["main"]["humidity"],
                    "wind_speed": data["wind"]["speed"],
                    "status": "success",
                    "fetched_at": datetime.datetime.now().isoformat()
                }
                logger.info(f"Successfully retrieved weather for: {location}")
                return weather_data
            else:
                logger.warning(
                    f"OpenWeatherMap returned status code {response.status_code}. "
                    f"Response: {response.text}. Falling back to mock data."
                )
                return get_mock_weather(location)
                
    except Exception as e:
        logger.error(f"Failed to fetch weather for {location} due to an exception: {e}. Falling back to mock data.")
        return get_mock_weather(location)

def get_mock_weather(location: str) -> dict[str, Any]:
    """
    Generates a deterministic and realistic mock weather forecast.
    """
    # Deterministic mock weather based on location length/characters
    loc_hash = sum(ord(c) for c in location)
    temp = 15.0 + (loc_hash % 15)  # Range 15 to 30
    feels_like = temp + 1.2 if (loc_hash % 2 == 0) else temp - 0.8
    humidity = 40 + (loc_hash % 45)  # Range 40 to 85
    wind_speed = 2.0 + (loc_hash % 8)  # Range 2.0 to 10.0
    
    conditions = ["Clear sky", "Partly cloudy", "Overcast", "Light rain", "Scattered clouds"]
    description = conditions[loc_hash % len(conditions)]
    
    return {
        "location": location,
        "temp": round(temp, 1),
        "feels_like": round(feels_like, 1),
        "description": description,
        "humidity": humidity,
        "wind_speed": round(wind_speed, 1),
        "status": "mocked",
        "fetched_at": datetime.datetime.now().isoformat()
    }

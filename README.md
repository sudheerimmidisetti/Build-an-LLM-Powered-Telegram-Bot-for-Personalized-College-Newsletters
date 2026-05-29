# LLM-Powered Telegram Bot for Personalized College Newsletters

A complete, production-ready backend service and Telegram Bot that delivers personalized weekly college newsletters containing styled campus events, academic course reminders, and weather outlooks. The styling of the newsletter is generated dynamically by local LLM (`llama3.1:8b`) via Ollama based on user preferences.

---

## Architecture Overview

The system is designed with a modular, async-first architecture utilizing Python 3.12:

```
                  ┌──────────────────────┐
                  │    Telegram Client   │
                  └──────────┬───────────┘
                             │ (commands: /start, /newsletter, etc.)
                             ▼
  ┌──────────────────────────────────────────────────────────────┐
  │                        Python App (bot)                      │
  │                                                              │
  │   ┌──────────────────┐  ┌──────────────────┐  ┌──────────┐   │
  │   │   Telegram Bot   │  │ FastAPI Endpoint │  │Scheduler │   │
  │   │    (polling)     │  │(/test-mcp-tool)  │  │ (weekly) │   │
  │   └────────┬─────────┘  └────────┬─────────┘  └────┬─────┘   │
  │            │                     │                 │         │
  │            ▼                     ▼                 ▼         │
  │     ┌─────────────┐       ┌─────────────┐    ┌───────────┐   │
  │     │  Jinja2     │       │  MCP Tools  │    │SQLAlchemy │   │
  │     │  Templates  │       │ (Services)  │    │  (SQLite) │   │
  │     └──────┬──────┘       └──────┬──────┘    └─────┬─────┘   │
  └────────────┼─────────────────────┼─────────────────┼─────────┘
               │                     │                 │
               │ (Jinja prompts)     │ (weather call)  │ (CRUD users, events, courses)
               ▼                     ▼                 ▼
        ┌──────────────┐     ┌──────────────┐   ┌──────────────┐
        │    Ollama    │     │ OpenWeather  │   │ newsletter.db│
        │(llama3.1:8b) │     │     API      │   │   (SQLite)   │
        └──────────────┘     └──────────────┘   └──────────────┘
```

1. **Telegram Bot Command Handlers**: Written in `python-telegram-bot`, utilizing a `ConversationHandler` state machine to manage user onboarding (/start) and subscription preferences.
2. **FastAPI Web Server**: Exposes evaluation endpoints for MCP tools (`POST /test-mcp-tool`) and healthchecks.
3. **Database Layer (SQLAlchemy + SQLite)**: Operates asynchronously using `sqlite+aiosqlite`. Automatically initializes tables and seeds mock data (10+ events and 10+ courses) on application boot.
4. **Model Context Protocol (MCP) Tools**: Exposes structured campus queries and weather integration.
5. **Ollama Integration (`llama3.1:8b`)**: Interacts with the local Ollama daemon. Uses a custom request wrapper with built-in retries, exponential backoffs, and formatting fail-safes.
6. **APScheduler**: Manages weekly cron deliveries asynchronously without blocking main thread execution.

---

## Folder Structure

```
project-root/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── bot/
│   │   ├── __init__.py
│   │   └── handlers.py
│   ├── database/
│   │   ├── __init__.py
│   │   └── connection.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py
│   ├── scheduler/
│   │   ├── __init__.py
│   │   └── scheduler.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── llm_service.py
│   ├── templates/
│   │   ├── courses.j2
│   │   ├── events.j2
│   │   ├── newsletter.j2
│   │   └── weather.j2
│   ├── tools/
│   │   ├── __init__.py
│   │   └── campus_tools.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── telegram_formatter.py
│   ├── __init__.py
│   └── main.py
├── data/
│   ├── newsletter.db
│   └── seed.py
├── .env
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── README.md
└── submission.json
```

---

## Setup & Configuration

### Prerequisites
- Python 3.12 (if running locally)
- Docker & Docker Compose (for containerized deployment)
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- OpenWeatherMap API Key (from [OpenWeatherMap](https://openweathermap.org/api))

### Environment Variables
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Populate the required keys in `.env`:
   - `TELEGRAM_BOT_TOKEN`: The token for your Telegram bot.
   - `OPENWEATHERMAP_API_KEY`: Key to fetch real weather conditions. If left blank, the application will automatically fall back to realistic mock forecasts for testing.

---

## Local Execution Instructions

To run the application locally outside of Docker:

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Start Ollama Locally**:
   - Ensure Ollama is installed on your machine and running.
   - Run: `ollama run llama3.1:8b` (this downloads the model locally).
   - In `.env`, set `OLLAMA_BASE_URL=http://localhost:11434`.
3. **Run the Application**:
   ```bash
   python -m app.main
   ```
   *Note: The SQLite database file will automatically be created and seeded at `data/newsletter.db`.*

---

## Docker Execution Instructions

Running the entire stack (Bot, FastAPI, and auto-configured Ollama) is simple and automated:

1. **Build and Run**:
   ```bash
   docker-compose up --build
   ```
2. **Automatic Model Pulling**:
   - The `ollama` container will boot up, serve the API, and automatically download `llama3.1:8b` via its customized entrypoint script.
   - The `bot` container has a dependency constraint: it will wait until the model has finished downloading and `ollama` passes its list-based healthcheck.
3. **Verify Health**:
   - You can inspect the health status of the containers with:
     ```bash
     docker ps
     ```
   - Once the health status of `ollama` is `healthy`, the `bot` will start and register handlers.

---

## Testing & Evaluation

### FastAPI Evaluation Endpoint
FastAPI is running on port `8000`. You can test the MCP tools by sending POST requests to the `/test-mcp-tool` endpoint.

#### 1. Test `get_weather_forecast`
```bash
curl -X POST http://localhost:8000/test-mcp-tool \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_weather_forecast", "tool_args": {"location": "New York,US"}}'
```

#### 2. Test `get_campus_events`
```bash
curl -X POST http://localhost:8000/test-mcp-tool \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_campus_events", "tool_args": {}}'
```

#### 3. Test `get_course_reminders`
```bash
curl -X POST http://localhost:8000/test-mcp-tool \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_course_reminders", "tool_args": {"program": "Computer Science"}}'
```

### Telegram Bot Commands
Open your Telegram app, search for your bot, and execute the following test flow:
1. **/start**: The bot will greet you and prompt you for your College and Program.
2. **/newsletter**: Generates and sends a newsletter matching your program and college weather.
3. **/unsubscribe**: Subscribes you out of the weekly deliveries.

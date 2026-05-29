FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr for logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install curl for the container healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and support directories
COPY app/ app/
COPY data/ data/

# Ensure the SQLite data directory is writable inside the container
RUN mkdir -p /app/data && chmod 777 /app/data

# Expose FastAPI port
EXPOSE 8000

# Define Docker healthcheck on the FastAPI endpoint
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/healthz || exit 1

# Launch the combined FastAPI and Bot application
CMD ["python", "-m", "app.main"]

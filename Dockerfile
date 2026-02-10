FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Run migrations then start the app
CMD ["sh", "-c", "alembic -c alembic/alembic.ini upgrade head && uvicorn src.api.main:app --host 0.0.0.0 --port 8000"]

FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py .
COPY config.yaml .

# Create directory for ChromaDB data
RUN mkdir -p /data/chromadb

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the FastMCP server
ENTRYPOINT ["python", "server.py"]

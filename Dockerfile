FROM python:3.13-slim

WORKDIR /app

# Install system dependencies (including git and nodejs/npm for ShadowObserver)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Qwen CLI
RUN npm install -g @qwen-code/qwen-code

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
# Copy application code structure
COPY api/ ./api/
COPY crawlers/ ./crawlers/
COPY models/ ./models/
COPY repositories/ ./repositories/
COPY services/ ./services/
COPY dependencies.py .
COPY settings.py .
COPY server.py .
COPY logger.py .
COPY utils.py .
COPY watcher.py .

# Create directory for ChromaDB data
RUN mkdir -p /data/chromadb

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the FastMCP server
ENTRYPOINT ["python", "server.py"]

# Production Dockerfile for Project Caspian Communication Agent
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create application user
RUN groupadd -g 1000 caspian && \
    useradd -u 1000 -g caspian -m -s /bin/bash caspian

WORKDIR /app

# Install Python dependencies first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application codebase
COPY --chown=caspian:caspian . .

# Ensure storage and documents directories exist and are writable
RUN mkdir -p /app/data /app/documents /app/logs && \
    chown -R caspian:caspian /app/data /app/documents /app/logs && \
    chmod +x /app/scripts/healthcheck.py

# Switch to unprivileged user
USER caspian

# Configure Docker healthcheck
HEALTHCHECK --interval=60s --timeout=10s --start-period=15s --retries=3 \
    CMD ["python3", "/app/scripts/healthcheck.py"]

# Default entrypoint starts Telegram bot with background scheduler
CMD ["python3", "main.py"]

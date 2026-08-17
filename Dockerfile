# Use official Python 3.12 slim image
FROM python:3.12-slim

# Install system dependencies: FFmpeg, Opus, and build tools
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libopus-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the bot's code
COPY . .

# Optional: create a non-root user for security
RUN useradd -m -u 1000 botuser && chown -R botuser /app
USER botuser

# Command to run the bot
CMD ["python", "run.py"]
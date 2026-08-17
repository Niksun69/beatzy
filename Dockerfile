# Use official Python 3.12 slim image
FROM python:3.12-slim

# Install system dependencies: FFmpeg, Opus, Git, and build tools
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libopus-dev \
    git \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Clone the Beatzy repository from GitHub
RUN git clone https://github.com/Niksun69/beatzy.git .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user for security
RUN useradd -m -u 1000 botuser && chown -R botuser /app
USER botuser

# Command to run the bot
CMD ["python", "run.py"]
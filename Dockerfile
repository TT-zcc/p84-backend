# Use the official Python 3.10 slim image based on Debian Bullseye
FROM python:3.10-slim-bullseye

# --------------------------------------
# Install system dependencies
# --------------------------------------
# - netcat (nc): Used to check database port availability
# - Clean up cache to reduce image size
RUN apt-get update \
    && apt-get install -y netcat \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# --------------------------------------
# Install Python dependencies
# --------------------------------------
# - Copy production requirements file
# - Install dependencies without caching to keep the image lightweight
COPY requirements/prod.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# --------------------------------------
# Copy application source code
# --------------------------------------
COPY . .

# --------------------------------------
# Expose application port
# --------------------------------------
# Flask will run on port 5000 inside the container
EXPOSE 5000

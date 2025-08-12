# Use the official Python 3.10 slim image based on Debian Bullseye
FROM python:3.10-slim-bullseye

# --------------------------------------
# Install system dependencies
# --------------------------------------
RUN apt-get update \
    && apt-get install -y --no-install-recommends netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# --------------------------------------
# Install Python dependencies
# --------------------------------------
COPY requirements/prod.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# --------------------------------------
# Copy application source code
# --------------------------------------
COPY . .

# Render will set the $PORT environment variable automatically
ENV PORT=5000

# --------------------------------------
# Start the Flask app via Gunicorn
# Bind to 0.0.0.0:$PORT so Render can route traffic
# --------------------------------------
CMD gunicorn --preload -w ${GUNICORN_WORKERS:-4} -b 0.0.0.0:${PORT} autoapp:app

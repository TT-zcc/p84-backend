# Use the official Python 3.10 slim image based on Debian Bullseye
FROM python:3.10-slim-bullseye

# --------------------------------------
# Install system dependencies
# --------------------------------------
# - netcat (nc): Used to check database port availability
# - Clean up cache to reduce image size
RUN apt-get update \
    && apt-get install -y --no-install-recommends netcat-openbsd \
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
# Render will set the $PORT environment variable automatically
# Do NOT hardcode 5000 — bind to 0.0.0.0:$PORT
# --------------------------------------
ENV PORT=5000

# --------------------------------------
# Start the Flask app via Gunicorn
# Bind to 0.0.0.0:$PORT so Render can route traffic
# --------------------------------------
CMD bash -c "while ! nc -z \${DB_HOST:-localhost} \${DB_PORT:-5432}; do echo 'Waiting for DB...'; sleep 1; done && gunicorn --preload -w \${GUNICORN_WORKERS:-4} -b 0.0.0.0:\${PORT} autoapp:app"

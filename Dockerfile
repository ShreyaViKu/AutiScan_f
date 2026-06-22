FROM python:3.12-slim

# Install system dependencies (needed for compiling certain python packages if necessary)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/cache/*

WORKDIR /app

# Copy requirements from the subfolder and install
COPY AutiScan3/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project code into the container
COPY . .

# Set working directory to the subfolder where app.py lives
WORKDIR /app/AutiScan3

# Hugging Face Spaces expects the application to run on port 7860
EXPOSE 7860

# Start Flask via gunicorn on port 7860
CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app"]

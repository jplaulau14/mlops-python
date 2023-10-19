# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory in the container to /app
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy app.py, requirements.txt, gx/, Dockerfile and train_synthesizer.py into the container at /app
COPY app.py requirements.txt gx/ Dockerfile train_synthesizer.py /app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create data and tmp directories
RUN mkdir data tmp

# Specify the command to run on container start
CMD ["gunicorn", "-w", "4", "app:app", "-b", "0.0.0.0:5000"]

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies needed for audio processing
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Set Python path
ENV PYTHONPATH=/app/src

# Expose port (Digital Ocean will inject $PORT)
EXPOSE $PORT

# Run the application
CMD cd src && python -m uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080}
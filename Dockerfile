FROM python:3.12-slim

WORKDIR /app

# Install system dependencies needed for audio processing
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt first for better caching
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Set Python path
ENV PYTHONPATH=/app/src

# Google Cloud Run injects PORT environment variable
ENV PORT=8080
EXPOSE $PORT

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Run the application (Google Cloud Run will inject $PORT)
CMD cd src && python -m uvicorn server:app --host 0.0.0.0 --port $PORT
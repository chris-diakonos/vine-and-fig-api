# Multi-stage build for Vine & Fig Building Designer API
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies required for CadQuery
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglu1-mesa \
    libxrender1 \
    libxext6 \
    libsm6 \
    libice6 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglu1-mesa \
    libxrender1 \
    libxext6 \
    libsm6 \
    libice6 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY ./src /app/src
#COPY .env.example /app/.env

# Create temp directories for generated files
RUN mkdir -p /app/temp/models /app/temp/drawings && \
    chmod -R 755 /app/temp

# Set Python path
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

# Argus 2.0 Security Platform - Production Docker Image
FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5001 \
    PYTHONPATH=/app/backend

# Install system dependencies including native Nmap CLI and network utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    net-tools \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency file first for Docker build caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy complete project code
COPY . .

# Expose port
EXPOSE 5001

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5001/ || exit 1

# Launch Gunicorn production WSGI server
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "--threads", "4", "--timeout", "120", "backend.app:app"]

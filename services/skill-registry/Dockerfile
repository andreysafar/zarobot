FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY services/skill-registry/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/skill-registry/ .
COPY blockchain/ ./blockchain/

# Create non-root user
RUN useradd -m -u 1000 skillregistry && \
    chown -R skillregistry:skillregistry /app
USER skillregistry

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

EXPOSE 8003

CMD ["python", "registry_service.py"]
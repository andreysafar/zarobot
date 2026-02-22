FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY services/bot-factory/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/bot-factory/ .
COPY blockchain/ ./blockchain/
COPY core/models.py ./core/
COPY apps/ ./apps/

# Create non-root user
RUN useradd -m -u 1000 botfactory && \
    chown -R botfactory:botfactory /app
USER botfactory

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

EXPOSE 8001

CMD ["python", "main.py"]
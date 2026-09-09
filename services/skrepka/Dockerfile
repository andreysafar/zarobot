FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY services/skrepka/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/skrepka/ .

RUN mkdir -p /data/skrepka

# Скрепка работает как background agent
CMD ["python", "agent.py"]

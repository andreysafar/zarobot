FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY services/core_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/core_api/ .

RUN mkdir -p /data/core_api

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

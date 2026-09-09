FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc \
    && rm -rf /var/lib/apt/lists/*

COPY services/dervaler/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/dervaler/ ./dervaler/
# Промпты сводки — только чтение.
COPY personalities/dervaler/ /app/personalities/dervaler/

# Каталог сессии монтируется с хоста и НЕ попадает в образ.
RUN mkdir -p /data/dervaler /data \
    && useradd -m -u 1000 dervaler \
    && chown -R dervaler:dervaler /app /data
USER dervaler

# Личность нужна только для промптов сводки — монтируем read-only.
VOLUME ["/data"]

HEALTHCHECK --interval=60s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import sqlite3,os; \
        p='/data/dervaler/archive.sqlite3'; \
        raise SystemExit(0 if (not os.path.exists(p)) else 0)" || exit 1

CMD ["python", "-m", "dervaler.worker"]

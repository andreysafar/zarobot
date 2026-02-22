FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY services/bot-instance/requirements.new.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/bot-instance/ .
COPY sdk/ /opt/zero-bot-sdk/
RUN pip install --no-cache-dir /opt/zero-bot-sdk/

RUN mkdir -p /data/skills /data/personality /data/state \
    && useradd -m -u 1000 botuser \
    && chown -R botuser:botuser /app /data
USER botuser

VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "print('ok')" || exit 1

CMD ["python", "bot.py"]

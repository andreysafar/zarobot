FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY services/bot-instance/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/bot-instance/ .
COPY sdk/ /opt/zero-bot-sdk/
RUN pip install --no-cache-dir /opt/zero-bot-sdk/

# The helper-kb skill reads the archive Dervaler writes, so the bot needs the
# `dervaler.store` module. Only the storage layer is used here - the worker
# itself runs in its own container and never starts from this image.
COPY services/dervaler/ ./dervaler/

# Copy every personality under /data/personality/<id>/.
# PersonalityLoader resolves <root>/<PERSONALITY> first (e.g. /data/personality/ia).
COPY personalities/ /data/personality/

RUN mkdir -p /data/skills /data/personality /data/state \
    && useradd -m -u 1000 botuser \
    && chown -R botuser:botuser /app /data
USER botuser

VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "print('ok')" || exit 1

CMD ["python", "bot.py"]

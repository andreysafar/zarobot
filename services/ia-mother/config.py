"""
IA-Mother configuration: env vars, debug logging, Redis, FastAPI health app.
"""

import os
from datetime import datetime
from pathlib import Path

# Debug log helper
_DBG_LOG = str(Path(__file__).resolve().parent.parent.parent / ".cursor" / "debug.log")


def _dbg(loc: str, msg: str, data: dict | None = None, hyp: str | None = None) -> None:
    import json as _j
    os.makedirs(os.path.dirname(_DBG_LOG), exist_ok=True)
    with open(_DBG_LOG, "a") as _f:
        _f.write(
            _j.dumps(
                {
                    "id": f"log_{int(datetime.now().timestamp() * 1000)}",
                    "timestamp": int(datetime.now().timestamp() * 1000),
                    "location": loc,
                    "message": msg,
                    "data": data or {},
                    "runId": "ia_mother_run",
                    "hypothesisId": hyp or "",
                }
            )
            + "\n"
        )


# Environment
TELEGRAM_BOT_TOKEN = os.getenv("IA_MOTHER_BOT_TOKEN")
CORE_API_URL = os.getenv("CORE_API_URL")
REDIS_URL = os.getenv("REDIS_URL")
TON_API_KEY = os.getenv("TON_API_KEY")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-domain.com")
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")

# Redis
redis_client = None
if REDIS_URL:
    try:
        import redis as _redis_mod
        redis_client = _redis_mod.from_url(REDIS_URL)
        _dbg("config:redis", "Redis connected", hyp="H3")
    except Exception as _re:
        _dbg("config:redis", f"Redis connection failed: {_re}", {"error": str(_re)}, "H3")

# FastAPI health app
health_app = None
try:
    from fastapi import FastAPI
    health_app = FastAPI(title="IA-Mother Bot")
except ImportError:
    pass

import os
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()


def _parse_redis_url(url: str) -> tuple[str, int, int]:
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    db = int((parsed.path or "/0").lstrip("/") or "0")
    return host, port, db


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_HOST, REDIS_PORT, REDIS_DB = _parse_redis_url(REDIS_URL)

import json
import logging
from typing import Any, Optional

import redis

logger = logging.getLogger(__name__)


class ComicJobStore:
    """Lưu trạng thái comic job trên Redis (JSON)."""

    def __init__(self, redis_url: str, ttl_sec: int = 86400):
        self._client = redis.from_url(redis_url, decode_responses=True)
        self._ttl_sec = ttl_sec
        self._prefix = "comic_job:"

    def _key(self, job_id: str) -> str:
        return f"{self._prefix}{job_id}"

    def save(self, job_id: str, payload: dict[str, Any]) -> None:
        key = self._key(job_id)
        self._client.setex(key, self._ttl_sec, json.dumps(payload, ensure_ascii=False))
        logger.debug("Saved job state: %s", job_id)

    def load(self, job_id: str) -> Optional[dict[str, Any]]:
        raw = self._client.get(self._key(job_id))
        if not raw:
            return None
        return json.loads(raw)

    def delete(self, job_id: str) -> None:
        self._client.delete(self._key(job_id))

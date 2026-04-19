"""
Redis Cache Layer for Recommendation Service.

Cache key format: recs:{user_id}:{experiment_group}
TTL: configurable (default 300s / 5 minutes)
"""

import json
import logging
from typing import Optional, Dict, Any

import redis.asyncio as redis

from .config import settings

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "recs"


class RecommendationCache:
    """Redis-backed recommendation cache."""

    def __init__(self):
        self.redis = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )

    def _build_key(self, user_id: str, experiment_group: str) -> str:
        return f"{CACHE_KEY_PREFIX}:{user_id}:{experiment_group}"

    async def get(self, user_id: str, experiment_group: str) -> Optional[Dict[str, Any]]:
        """Get cached recommendations. Returns None on miss."""
        key = self._build_key(user_id, experiment_group)
        try:
            cached = await self.redis.get(key)
            if cached:
                logger.debug(f"Cache hit for {key}")
                return json.loads(cached)
        except redis.RedisError as e:
            logger.error(f"Redis read error: {e}")
        return None

    async def set(self, user_id: str, experiment_group: str, data: Dict[str, Any]):
        """Store recommendations with TTL."""
        key = self._build_key(user_id, experiment_group)
        try:
            await self.redis.set(key, json.dumps(data), ex=settings.cache_ttl_seconds)
            logger.debug(f"Cached {key} with TTL={settings.cache_ttl_seconds}s")
        except redis.RedisError as e:
            logger.error(f"Redis write error: {e}")


cache = RecommendationCache()

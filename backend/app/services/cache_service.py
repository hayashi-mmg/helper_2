import json
import logging
from typing import Any

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# TTL設定（秒）
TTL_RECIPE = 3600       # 1時間
TTL_SESSION = 1800      # 30分
TTL_MENU = 21600        # 6時間

_redis_pool: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_pool


async def cache_get(key: str) -> Any | None:
    try:
        r = await get_redis()
        value = await r.get(key)
        if value:
            return json.loads(value)
    except Exception as e:
        logger.warning(f"Cache get failed for key={key}: {e}")
    return None


async def cache_set(key: str, value: Any, ttl: int = TTL_RECIPE) -> None:
    try:
        r = await get_redis()
        await r.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception as e:
        logger.warning(f"Cache set failed for key={key}: {e}")


async def cache_delete(key: str) -> None:
    try:
        r = await get_redis()
        await r.delete(key)
    except Exception as e:
        logger.warning(f"Cache delete failed for key={key}: {e}")


async def cache_delete_pattern(pattern: str) -> None:
    try:
        r = await get_redis()
        async for key in r.scan_iter(match=pattern):
            await r.delete(key)
    except Exception as e:
        logger.warning(f"Cache delete pattern failed for {pattern}: {e}")

import logging
import time

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.core.database import async_session
from app.websocket.manager import manager as ws_manager

logger = logging.getLogger(__name__)
router = APIRouter()

# アプリ起動時刻
_start_time = time.time()


async def _check_database() -> dict:
    try:
        async with async_session() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


async def _check_redis() -> dict:
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.ping()
        await r.aclose()
        return {"status": "healthy"}
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


@router.get("/health")
async def health_check():
    db_status = await _check_database()
    redis_status = await _check_redis()

    overall = "healthy"
    if db_status["status"] != "healthy":
        overall = "degraded"
    if redis_status["status"] != "healthy":
        overall = "degraded" if overall == "healthy" else overall

    return {
        "status": overall,
        "version": "1.0.0",
        "uptime_seconds": round(time.time() - _start_time),
        "services": {
            "database": db_status,
            "redis": redis_status,
        },
    }


@router.get("/metrics")
async def metrics():
    db_status = await _check_database()
    redis_status = await _check_redis()

    return {
        "uptime_seconds": round(time.time() - _start_time),
        "websocket_connections": ws_manager.active_connections_count,
        "services": {
            "database": db_status["status"],
            "redis": redis_status["status"],
        },
    }

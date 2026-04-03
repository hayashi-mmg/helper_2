import logging
import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """セキュリティヘッダーを付与するミドルウェア。"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """リクエストのレスポンスタイムをログに記録するミドルウェア。"""

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000

        if duration_ms > 500:
            logger.warning(f"Slow request: {request.method} {request.url.path} took {duration_ms:.0f}ms")
        else:
            logger.info(f"{request.method} {request.url.path} {response.status_code} {duration_ms:.0f}ms")

        response.headers["X-Response-Time"] = f"{duration_ms:.0f}ms"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """シンプルなインメモリレート制限ミドルウェア。"""

    def __init__(self, app):
        super().__init__(app)
        # IP -> list of timestamps
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = 3600  # 1 hour

        # 古いエントリを削除
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if now - t < window
        ]

        # 認証ヘッダの有無でレート制限を分ける
        has_auth = "authorization" in request.headers
        limit = settings.RATE_LIMIT_AUTHENTICATED if has_auth else settings.RATE_LIMIT_UNAUTHENTICATED

        if len(self._requests[client_ip]) >= limit:
            return Response(
                content='{"error":{"code":"RATE_LIMIT_EXCEEDED","message":"リクエスト数が上限を超えました"}}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "3600"},
            )

        self._requests[client_ip].append(now)
        return await call_next(request)

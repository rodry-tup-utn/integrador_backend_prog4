from datetime import datetime, timezone
from typing import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.exceptions import RateLimitExceededError
from app.core.rate_limiter import RateLimiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware que aplica rate limiting a cada request.
    """

    # Registry de instances activas (para tests).
    _instances: list["RateLimitMiddleware"] = []

    # Paths que matchean el auth_limiter (más estricto).
    AUTH_PATHS: tuple[str, ...] = ("/auth/", "/profile/password")

    EXCLUDED_PATHS: set[str] = {
        "/health",
        "/",
        "/favicon.ico",
        "/openapi.json",
        "/docs",
        "/redoc",
    }

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

        self.default_limiter = RateLimiter(
            capacity=settings.rate_limit_default_burst,
            refill_rate_per_minute=settings.rate_limit_default_per_minute,
        )
        self.auth_limiter = RateLimiter(
            capacity=settings.rate_limit_auth_burst,
            refill_rate_per_minute=settings.rate_limit_auth_per_minute,
        )

        RateLimitMiddleware._instances.append(self)

    @classmethod
    def reset_all_limiters(cls) -> None:
        """
        Resetea los buckets de TODAS las instances activas.
        """
        for instance in cls._instances:
            instance.default_limiter.reset_all()
            instance.auth_limiter.reset_all()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        Aplica rate limiting y agrega headers X-RateLimit-* a la response.
        """
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        limiter = (
            self.auth_limiter
            if any(request.url.path.startswith(p) for p in self.AUTH_PATHS)
            else self.default_limiter
        )
        client_key = self._get_client_key(request)

        if not limiter.is_allowed(client_key):

            seconds_until_next_token = int(1 / max(limiter.refill_rate, 0.001))
            exc = RateLimitExceededError(
                retry_after=seconds_until_next_token,
                limit=int(limiter.capacity),
                remaining=0,
            )

            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                        "request_id": None,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "retry_after": exc.retry_after,
                    }
                },
                headers={
                    "Retry-After": str(seconds_until_next_token),
                    "X-RateLimit-Limit": str(exc.limit),
                    "X-RateLimit-Remaining": str(exc.remaining),
                },
            )

        response = await call_next(request)

        response.headers["X-RateLimit-Limit"] = str(limiter.capacity)
        response.headers["X-RateLimit-Remaining"] = str(
            limiter.get_remaining(client_key)
        )

        return response

    @staticmethod
    def _get_client_key(request: Request) -> str:
        """
        Construye la key del cliente para el bucket.

        Estrategia:
          1. Si hay header X-Forwarded-For (proxy reverso), usamos la primera IP.
          2. Si no, usamos request.client.host (conexión directa).
        """
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        if request.client:
            return f"ip:{request.client.host}"
        return "ip:unknown"

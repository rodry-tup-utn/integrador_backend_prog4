import time
import uuid
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logger import get_logger

# Logger específico para este middleware.
logger = get_logger("app.middleware.logging")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware que registra cada request y su response correspondiente.
    """

    EXCLUDED_PATHS: set[str] = {
        "/health",
        "/favicon.ico",
        "/openapi.json",
        "/docs",
        "/redoc",
    }

    def __init__(self, app: ASGIApp, log_body: bool = False) -> None:
        """
        Args:
            app: la siguiente capa en la cadena ASGI.
            log_body: si True, loggea el body de la response (peligroso en prod).
        """
        super().__init__(app)
        self.log_body = log_body

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:

        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        request.state.request_id = request_id

        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        logger.info(
            "→ %s %s [id=%s] from=%s",
            request.method,
            request.url.path,
            request_id[:8],
            self._get_client_ip(request),
        )
        try:
            response = await call_next(request)
        except Exception as exc:

            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "✗ %s %s [id=%s] EXCEPTION after %.1fms: %s",
                request.method,
                request.url.path,
                request_id[:8],
                duration_ms,
                repr(exc),
            )
            raise
        duration_ms = (time.perf_counter() - start_time) * 1000

        if response.status_code >= 500:
            log_level = logger.error
        elif response.status_code >= 400:
            log_level = logger.warning
        else:
            log_level = logger.info

        log_level(
            "← %s %s [id=%s] %d in %.1fms",
            request.method,
            request.url.path,
            request_id[:8],
            response.status_code,
            duration_ms,
        )

        response.headers["X-Request-ID"] = request_id

        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """
        Extrae la IP del cliente, considerando proxies.
        """
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # X-Forwarded-For: "client, proxy1, proxy2"
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

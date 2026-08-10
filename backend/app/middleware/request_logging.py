"""HTTP middleware."""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.bind(request_id=request_id).info(
            "{method} {path} -> {status} ({duration:.2f}ms)",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration=duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response

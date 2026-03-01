"""Structured request logging middleware.

Logs each request with method, path, status code, duration, and client IP.
Uses Python's standard logging — can be forwarded to any log aggregator.
"""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("evograph.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with structured fields."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start = time.monotonic()

        # Attach request ID to response headers for tracing
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000

        forwarded = request.headers.get("x-forwarded-for")
        client_ip = forwarded.split(",")[0].strip() if forwarded else (
            request.client.host if request.client else "unknown"
        )

        logger.info(
            "%s %s %d %.1fms client=%s req=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            client_ip,
            request_id,
        )

        response.headers["X-Request-ID"] = request_id
        return response

"""Sliding-window rate limiting middleware.

Simple in-memory rate limiter suitable for single-instance deployment.
For multi-instance, swap to Redis-backed (SCOPE_OTT_ROOT already has Redis URL configured).

Limits by client IP address. Returns 429 with Retry-After header when exceeded.
"""

from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP sliding window rate limiter.

    Args:
        app: The ASGI application.
        max_requests: Maximum requests per window.
        window_seconds: Window duration in seconds.
        exclude_paths: Paths to exclude from rate limiting (e.g. health checks).
    """

    def __init__(
        self,
        app,
        max_requests: int = 100,
        window_seconds: int = 60,
        exclude_paths: tuple[str, ...] = ("/health", "/docs", "/openapi.json"),
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exclude_paths = exclude_paths
        # {ip: [timestamp, timestamp, ...]}
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = time.monotonic()
        self._cleanup_interval = 300.0  # clean up stale entries every 5 min

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, respecting X-Forwarded-For behind a proxy."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _cleanup_stale(self, now: float) -> None:
        """Remove entries for IPs that haven't been seen recently."""
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now
        cutoff = now - self.window_seconds * 2
        stale_keys = [ip for ip, hits in self._hits.items() if not hits or hits[-1] < cutoff]
        for key in stale_keys:
            del self._hits[key]

    async def dispatch(self, request: Request, call_next):
        # Skip excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        now = time.monotonic()
        self._cleanup_stale(now)

        ip = self._get_client_ip(request)
        window_start = now - self.window_seconds

        # Trim old hits outside the window
        hits = self._hits[ip]
        while hits and hits[0] < window_start:
            hits.pop(0)

        if len(hits) >= self.max_requests:
            retry_after = int(hits[0] - window_start) + 1
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        hits.append(now)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(self.max_requests - len(hits))
        return response

"""
Global HTTP middleware for GFP CoreX.

This app is multi-tenant: a single ASGI application fronts every configuration,
so request-size and rate limits are enforced globally and tuned via environment
variables rather than per-config YAML.
"""

import os
import time
from collections import defaultdict, deque

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


def _int_env(name: str, default: int) -> int:
    """Read an integer environment variable, falling back to ``default``."""
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """Reject requests whose declared body exceeds ``max_bytes``."""

    def __init__(self, app, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid Content-Length header"},
                )
            if declared > self.max_bytes:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"detail": "Request body too large"},
                )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding-window rate limiter keyed by client IP.

    Suitable for single-process deployments. For multi-process or distributed
    setups, front the app with a shared limiter (e.g. Redis/NGINX) instead.
    """

    def __init__(self, app, limit_per_minute: int):
        super().__init__(app)
        self.limit = limit_per_minute
        self._hits: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if self.limit <= 0:  # Non-positive limit disables throttling.
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window_start = now - 60.0
        hits = self._hits[client_ip]

        # Drop timestamps that fell out of the trailing 60s window.
        while hits and hits[0] < window_start:
            hits.popleft()

        if len(hits) >= self.limit:
            retry_after = max(1, int(60 - (now - hits[0])))
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )

        hits.append(now)
        return await call_next(request)


def add_security_middleware(app) -> None:
    """Attach the global size/rate-limit middleware, configured from the environment.

    Environment variables:
        GFP_MAX_REQUEST_BYTES   Maximum request body size in bytes (default 10 MiB).
        GFP_RATE_LIMIT_PER_MIN  Requests/minute per client IP (default 100; <= 0 disables).
    """
    max_bytes = _int_env("GFP_MAX_REQUEST_BYTES", 10 * 1024 * 1024)
    rate_limit = _int_env("GFP_RATE_LIMIT_PER_MIN", 100)

    app.add_middleware(RateLimitMiddleware, limit_per_minute=rate_limit)
    app.add_middleware(MaxBodySizeMiddleware, max_bytes=max_bytes)

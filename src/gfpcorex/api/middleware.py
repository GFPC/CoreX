"""
Global HTTP middleware for GFP CoreX.

This app is multi-tenant: a single ASGI application fronts every configuration,
so request-size and rate limits are enforced globally and tuned via environment
variables rather than per-config YAML.
"""

import os
import time
from collections import defaultdict, deque
from typing import Optional, Tuple

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
    """Per-client-IP rate limiter with two interchangeable backends.

    * **Redis (distributed)** — used when a Redis URL is configured. A shared
      fixed-window counter (atomic ``INCR`` + first-hit ``EXPIRE`` via a Lua
      script) enforces *one consistent limit across every process and container*
      behind the load balancer. This is what makes the limit meaningful in the
      ``docker-compose.scale.yml`` topology, where three app instances would
      otherwise each keep their own private counter.
    * **In-memory (per-process sliding window)** — the fallback when no Redis URL
      is set, or whenever a Redis call fails. A Redis blip therefore degrades to
      local limiting instead of either dropping the limit or erroring requests.
    """

    _WINDOW_SECONDS = 60

    # Atomic increment + expiry-on-first-hit, returning {count, ttl}. Doing this
    # in one server-side script avoids the incr/expire race a client pipeline has.
    _LUA_INCR = """
    local current = redis.call('INCR', KEYS[1])
    if current == 1 then
        redis.call('EXPIRE', KEYS[1], ARGV[1])
    end
    return {current, redis.call('TTL', KEYS[1])}
    """

    def __init__(self, app, limit_per_minute: int, redis_url: Optional[str] = None):
        super().__init__(app)
        self.limit = limit_per_minute
        self._redis_url = redis_url
        self._redis = None
        self._redis_error_logged = False
        # Fallback state: client_ip -> monotonic timestamps within the window.
        self._hits: dict[str, deque] = defaultdict(deque)

    def _get_redis(self):
        """Lazily construct the async Redis client (bound to the running loop)."""
        if self._redis is None and self._redis_url:
            import redis.asyncio as aioredis

            self._redis = aioredis.Redis.from_url(self._redis_url)
        return self._redis

    async def dispatch(self, request: Request, call_next):
        if self.limit <= 0:  # Non-positive limit disables throttling.
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        allowed, retry_after = await self._is_allowed(client_ip)
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)

    async def _is_allowed(self, client_ip: str) -> Tuple[bool, int]:
        """Return ``(allowed, retry_after_seconds)`` for this client."""
        redis_client = self._get_redis()
        if redis_client is not None:
            try:
                window = int(time.time()) // self._WINDOW_SECONDS
                key = f"gfp:rl:{client_ip}:{window}"
                count, ttl = await redis_client.eval(
                    self._LUA_INCR, 1, key, self._WINDOW_SECONDS
                )
                if int(count) > self.limit:
                    return False, max(1, int(ttl))
                return True, 0
            except Exception as e:  # Redis down/unreachable → degrade locally.
                if not self._redis_error_logged:
                    self._redis_error_logged = True
                    print(
                        "⚠️  Rate-limit Redis unavailable, falling back to "
                        f"in-memory limiter: {e}"
                    )

        return self._is_allowed_in_memory(client_ip)

    def _is_allowed_in_memory(self, client_ip: str) -> Tuple[bool, int]:
        now = time.monotonic()
        window_start = now - float(self._WINDOW_SECONDS)
        hits = self._hits[client_ip]

        # Drop timestamps that fell out of the trailing window.
        while hits and hits[0] < window_start:
            hits.popleft()

        if len(hits) >= self.limit:
            retry_after = max(1, int(self._WINDOW_SECONDS - (now - hits[0])))
            return False, retry_after

        hits.append(now)
        return True, 0


def add_security_middleware(app) -> None:
    """Attach the global size/rate-limit middleware, configured from the environment.

    Environment variables:
        GFP_MAX_REQUEST_BYTES      Maximum request body size in bytes (default 10 MiB).
        GFP_RATE_LIMIT_PER_MIN     Requests/minute per client IP (default 100; <= 0 disables).
        GFP_RATE_LIMIT_REDIS_URL   Optional Redis URL for a shared, cross-instance
                                   limiter (e.g. ``redis://redis:6379/1``). When unset,
                                   an in-memory per-process limiter is used instead.
    """
    max_bytes = _int_env("GFP_MAX_REQUEST_BYTES", 10 * 1024 * 1024)
    rate_limit = _int_env("GFP_RATE_LIMIT_PER_MIN", 100)
    rate_limit_redis_url = os.environ.get("GFP_RATE_LIMIT_REDIS_URL") or None

    app.add_middleware(
        RateLimitMiddleware,
        limit_per_minute=rate_limit,
        redis_url=rate_limit_redis_url,
    )
    app.add_middleware(MaxBodySizeMiddleware, max_bytes=max_bytes)

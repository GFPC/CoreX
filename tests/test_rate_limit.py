"""
Unit tests for the security middleware — the in-memory rate-limiter logic and
the request body-size guard.

The Redis-backed rate-limit path needs a live server and is exercised in the
scale stack, not here; these tests cover the pure, deterministic fallback logic.
"""

import src.gfpcorex.api.middleware as middleware_module
from src.gfpcorex.api.middleware import MaxBodySizeMiddleware, RateLimitMiddleware


class _FakeRequest:
    """Minimal stand-in exposing only the ``.headers`` dispatch() reads."""

    def __init__(self, content_length=None):
        self.headers = {}
        if content_length is not None:
            self.headers["content-length"] = content_length


# ── Rate limiter (in-memory fallback) ────────────────────────────────────────


def test_in_memory_allows_up_to_limit_then_blocks():
    mw = RateLimitMiddleware(app=None, limit_per_minute=3)
    ip = "10.0.0.1"

    assert mw._is_allowed_in_memory(ip)[0] is True
    assert mw._is_allowed_in_memory(ip)[0] is True
    assert mw._is_allowed_in_memory(ip)[0] is True

    allowed, retry_after = mw._is_allowed_in_memory(ip)
    assert allowed is False
    assert 1 <= retry_after <= 60


def test_in_memory_limits_are_per_ip():
    mw = RateLimitMiddleware(app=None, limit_per_minute=1)

    assert mw._is_allowed_in_memory("a")[0] is True
    assert mw._is_allowed_in_memory("a")[0] is False  # "a" is now exhausted
    assert mw._is_allowed_in_memory("b")[0] is True  # "b" is independent


def test_in_memory_window_slides(monkeypatch):
    mw = RateLimitMiddleware(app=None, limit_per_minute=1)
    clock = {"now": 1000.0}
    monkeypatch.setattr(middleware_module.time, "monotonic", lambda: clock["now"])

    assert mw._is_allowed_in_memory("x")[0] is True
    assert mw._is_allowed_in_memory("x")[0] is False

    clock["now"] += 61  # advance past the 60s window
    assert mw._is_allowed_in_memory("x")[0] is True


async def test_dispatch_disabled_when_limit_non_positive():
    mw = RateLimitMiddleware(app=None, limit_per_minute=0)

    async def call_next(_request):
        return "passthrough"

    # A non-positive limit disables throttling entirely; request is untouched.
    result = await mw.dispatch(object(), call_next)
    assert result == "passthrough"


# ── Max body size ────────────────────────────────────────────────────────────


async def test_body_size_rejects_oversized():
    mw = MaxBodySizeMiddleware(app=None, max_bytes=100)

    async def call_next(_request):
        return "OK"

    response = await mw.dispatch(_FakeRequest("101"), call_next)
    assert response.status_code == 413


async def test_body_size_rejects_invalid_length():
    mw = MaxBodySizeMiddleware(app=None, max_bytes=100)

    async def call_next(_request):
        return "OK"

    response = await mw.dispatch(_FakeRequest("not-a-number"), call_next)
    assert response.status_code == 400


async def test_body_size_allows_within_limit():
    mw = MaxBodySizeMiddleware(app=None, max_bytes=100)

    async def call_next(_request):
        return "OK"

    assert await mw.dispatch(_FakeRequest("50"), call_next) == "OK"


async def test_body_size_allows_missing_header():
    mw = MaxBodySizeMiddleware(app=None, max_bytes=100)

    async def call_next(_request):
        return "OK"

    assert await mw.dispatch(_FakeRequest(None), call_next) == "OK"

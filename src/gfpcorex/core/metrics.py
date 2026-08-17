"""
Prometheus metrics for GFP CoreX — dependency-free.

This module implements just enough of the Prometheus text exposition format
(https://prometheus.io/docs/instrumenting/exposition_formats/) to expose the
three signals that matter for a high-load service — the "RED" metrics:

    * Rate    — ``gfp_http_requests_total``            (counter)
    * Errors  — derivable from the ``status`` label on that counter
    * Duration — ``gfp_http_request_duration_seconds``  (histogram)

plus an in-progress gauge. It is deliberately implemented with the standard
library alone so it adds no dependency and cannot drift the Poetry lock.

Concurrency: the app runs one asyncio event loop per process, so the counter
mutations below are never preempted mid-update (no ``await`` between read and
write). Metrics are therefore per-process; horizontal scaling exposes one
``/metrics`` endpoint per instance and Prometheus aggregates across them — which
is exactly how the ``docker-compose.scale.yml`` topology scrapes app1/app2/app3.
"""

from __future__ import annotations

import time
from typing import Dict, List, Tuple

# Histogram bucket upper bounds in seconds. Chosen to straddle the latency band
# of a healthy async API (sub-10ms) through to slow outliers (multiple seconds).
_BUCKETS: Tuple[float, ...] = (
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0,
)

# (method, path, status) -> count
_requests_total: Dict[Tuple[str, str, str], int] = {}
# (method, path) -> per-bucket observation counts, index-aligned with _BUCKETS
#                    plus a trailing slot for the implicit +Inf bucket.
_duration_buckets: Dict[Tuple[str, str], List[int]] = {}
# (method, path) -> summed observed seconds
_duration_sum: Dict[Tuple[str, str], float] = {}
# (method, path) -> total observation count
_duration_count: Dict[Tuple[str, str], int] = {}

_in_progress: int = 0

PROMETHEUS_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


def inc_in_progress() -> None:
    global _in_progress
    _in_progress += 1


def dec_in_progress() -> None:
    global _in_progress
    _in_progress -= 1


def observe(method: str, path: str, status: int, duration_seconds: float) -> None:
    """Record one finished HTTP request."""
    _requests_total[(method, path, str(status))] = (
        _requests_total.get((method, path, str(status)), 0) + 1
    )

    key = (method, path)
    buckets = _duration_buckets.get(key)
    if buckets is None:
        buckets = [0] * (len(_BUCKETS) + 1)  # +1 for the +Inf overflow bucket
        _duration_buckets[key] = buckets

    # Increment only the single bucket the observation lands in; the exposition
    # renderer turns these into the cumulative ``le`` counts Prometheus expects.
    placed = False
    for i, upper in enumerate(_BUCKETS):
        if duration_seconds <= upper:
            buckets[i] += 1
            placed = True
            break
    if not placed:
        buckets[-1] += 1  # +Inf

    _duration_sum[key] = _duration_sum.get(key, 0.0) + duration_seconds
    _duration_count[key] = _duration_count.get(key, 0) + 1


def reset() -> None:
    """Clear all series. Intended for tests."""
    global _in_progress
    _requests_total.clear()
    _duration_buckets.clear()
    _duration_sum.clear()
    _duration_count.clear()
    _in_progress = 0


def _escape_label_value(value: str) -> str:
    """Escape a label value per the exposition format (backslash, quote, newline)."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _labels(**pairs: str) -> str:
    inner = ",".join(f'{k}="{_escape_label_value(v)}"' for k, v in pairs.items())
    return "{" + inner + "}"


def render_latest() -> str:
    """Render every series in Prometheus text exposition format."""
    lines: List[str] = []

    # ── Counter: total requests ────────────────────────────────────────────
    lines.append("# HELP gfp_http_requests_total Total HTTP requests processed.")
    lines.append("# TYPE gfp_http_requests_total counter")
    for (method, path, status), count in sorted(_requests_total.items()):
        labels = _labels(method=method, path=path, status=status)
        lines.append(f"gfp_http_requests_total{labels} {count}")

    # ── Gauge: in-progress requests ────────────────────────────────────────
    lines.append("# HELP gfp_http_requests_in_progress In-flight HTTP requests.")
    lines.append("# TYPE gfp_http_requests_in_progress gauge")
    lines.append(f"gfp_http_requests_in_progress {_in_progress}")

    # ── Histogram: request duration ────────────────────────────────────────
    lines.append(
        "# HELP gfp_http_request_duration_seconds HTTP request latency in seconds."
    )
    lines.append("# TYPE gfp_http_request_duration_seconds histogram")
    for (method, path) in sorted(_duration_buckets.keys()):
        buckets = _duration_buckets[(method, path)]
        cumulative = 0
        for i, upper in enumerate(_BUCKETS):
            cumulative += buckets[i]
            labels = _labels(method=method, path=path, le=_format_float(upper))
            lines.append(
                f"gfp_http_request_duration_seconds_bucket{labels} {cumulative}"
            )
        # +Inf bucket must equal the total observation count.
        cumulative += buckets[-1]
        labels = _labels(method=method, path=path, le="+Inf")
        lines.append(f"gfp_http_request_duration_seconds_bucket{labels} {cumulative}")

        pair_labels = _labels(method=method, path=path)
        lines.append(
            f"gfp_http_request_duration_seconds_sum{pair_labels} "
            f"{_duration_sum[(method, path)]}"
        )
        lines.append(
            f"gfp_http_request_duration_seconds_count{pair_labels} "
            f"{_duration_count[(method, path)]}"
        )

    return "\n".join(lines) + "\n"


def _format_float(value: float) -> str:
    """Render bucket bounds without a trailing ``.0`` where they are integers."""
    if value == int(value):
        return str(int(value))
    return repr(value)


# ── ASGI middleware ────────────────────────────────────────────────────────
# Imported lazily-safe: starlette is always present (FastAPI depends on it).
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402
from starlette.requests import Request  # noqa: E402


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Times every request and records it into the module-level registry.

    The ``path`` label uses the *matched route template* (e.g.
    ``/api/c/{config_name}/api/v1/auth/login``) rather than the concrete URL, so
    per-tenant traffic collapses onto a single low-cardinality series instead of
    exploding one series per config name. Unmatched requests (404s) are bucketed
    under ``__unmatched__`` for the same reason.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        inc_in_progress()
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = time.perf_counter() - start
            dec_in_progress()
            route = request.scope.get("route")
            path = getattr(route, "path", None) or "__unmatched__"
            observe(method, path, status_code, duration)

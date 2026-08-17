"""
Unit tests for the dependency-free Prometheus metrics module.

These exercise the exposition renderer and the in-memory registry directly —
no HTTP server, database, or Redis required.
"""

from src.gfpcorex.core.metrics import (
    PROMETHEUS_CONTENT_TYPE,
    _escape_label_value,
    dec_in_progress,
    inc_in_progress,
    observe,
    render_latest,
    reset,
)


def test_content_type_is_prometheus_v004():
    assert "version=0.0.4" in PROMETHEUS_CONTENT_TYPE


def test_observe_increments_request_counter():
    reset()
    observe("GET", "/widgets", 200, 0.01)
    observe("GET", "/widgets", 200, 0.02)
    out = render_latest()

    assert "# TYPE gfp_http_requests_total counter" in out
    assert (
        'gfp_http_requests_total{method="GET",path="/widgets",status="200"} 2' in out
    )


def test_histogram_buckets_are_cumulative_and_match_count():
    reset()
    # Three durations that land in three different buckets.
    for duration in (0.001, 0.2, 3.0):
        observe("GET", "/x", 200, duration)
    out = render_latest()

    bucket_values = [
        int(line.rsplit(" ", 1)[1])
        for line in out.splitlines()
        if line.startswith(
            'gfp_http_request_duration_seconds_bucket{method="GET",path="/x"'
        )
    ]

    # Cumulative buckets must be non-decreasing, and the final (+Inf) bucket must
    # equal the total number of observations.
    assert bucket_values == sorted(bucket_values)
    assert bucket_values[-1] == 3
    assert 'le="+Inf"' in out
    assert 'gfp_http_request_duration_seconds_count{method="GET",path="/x"} 3' in out


def test_sum_accumulates_observed_seconds():
    reset()
    observe("POST", "/y", 201, 0.1)
    observe("POST", "/y", 201, 0.4)
    out = render_latest()

    assert 'gfp_http_request_duration_seconds_count{method="POST",path="/y"} 2' in out
    sum_lines = [
        line
        for line in out.splitlines()
        if line.startswith(
            'gfp_http_request_duration_seconds_sum{method="POST",path="/y"}'
        )
    ]
    assert sum_lines, "sum line missing"
    assert abs(float(sum_lines[0].rsplit(" ", 1)[1]) - 0.5) < 1e-9


def test_in_progress_gauge_tracks_inflight():
    reset()
    inc_in_progress()
    inc_in_progress()
    dec_in_progress()
    out = render_latest()

    assert "# TYPE gfp_http_requests_in_progress gauge" in out
    assert "gfp_http_requests_in_progress 1" in out


def test_reset_clears_series():
    observe("GET", "/z", 200, 0.01)
    reset()
    out = render_latest()

    assert "gfp_http_requests_total{" not in out
    assert "gfp_http_requests_in_progress 0" in out


def test_label_values_are_escaped():
    assert _escape_label_value('a"b') == 'a\\"b'
    assert _escape_label_value("a\\b") == "a\\\\b"
    assert _escape_label_value("a\nb") == "a\\nb"


def test_render_escapes_path_label():
    reset()
    observe("GET", 'p"q', 200, 0.01)
    out = render_latest()
    assert 'path="p\\"q"' in out

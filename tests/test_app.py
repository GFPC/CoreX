"""
Unit tests for the GFP CoreX application factory (``create_app``).

These exercise ``create_app`` and ``_gather_cors_settings`` without entering the
ASGI lifespan (no ``TestClient`` context), so they need neither a database nor
Redis. They validate route mounting, middleware wiring, and the CORS policy that
falls back gracefully when a configuration fails to load (e.g. an unset secret).
"""

from src.gfpcorex.main import _gather_cors_settings, create_app


def _route_paths(app) -> set[str]:
    """Collect every route path registered on the application."""
    return {path for r in app.routes if (path := getattr(r, "path", None))}


def _middleware_names(app) -> set[str]:
    """Collect the class names of the app's user-configured middleware."""
    return {getattr(m, "cls", type(None)).__name__ for m in app.user_middleware}


def test_create_app_returns_configured_instance():
    """The factory builds a titled FastAPI app without touching the database."""
    app = create_app()
    assert app.title == "GFP CoreX"
    assert app.version == "1.0.0"


def test_create_app_mounts_expected_routes():
    """Core endpoints and the per-configuration routers are all mounted."""
    paths = _route_paths(create_app())

    # Global endpoints
    assert "/" in paths
    assert "/health" in paths
    assert "/health/{config_name}" in paths

    # Universal auth router (mounted under the per-config prefix)
    assert any(p.endswith("/auth/login") for p in paths)
    assert any(p.endswith("/auth/register") for p in paths)

    # Configuration-management router
    assert any("/api/v1/configs" in p for p in paths)


def test_create_app_wires_cors_and_security_middleware():
    """CORS plus the request-size / rate-limit middleware are all installed."""
    names = _middleware_names(create_app())
    assert "CORSMiddleware" in names
    assert "RateLimitMiddleware" in names
    assert "MaxBodySizeMiddleware" in names


def test_gather_cors_settings_contract():
    """CORS settings are a (origins, allow_credentials) pair with the wildcard invariant.

    Browsers reject a wildcard origin combined with credentials, so the two must
    never be enabled together.
    """
    origins, allow_credentials = _gather_cors_settings()

    assert isinstance(origins, list)
    assert all(isinstance(o, str) for o in origins)
    assert isinstance(allow_credentials, bool)

    if "*" in origins:
        assert allow_credentials is False

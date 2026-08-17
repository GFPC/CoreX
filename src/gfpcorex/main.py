"""
Main FastAPI application for GFP CoreX.
Multi-configuration backend with dynamic routing.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import List, Tuple

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware

from .api.config import create_config_router
from .api.middleware import add_security_middleware
from .core.config import get_available_configs, get_config
from .core.database import close_database, init_database, ping_database
from .core.metrics import (
    PROMETHEUS_CONTENT_TYPE,
    PrometheusMiddleware,
    render_latest,
)
from .core.redis_manager import close_redis, init_redis, redis_manager
from .utils.logging import GFPConsoleMessageStylizer

ConsoleMessageStylizer = GFPConsoleMessageStylizer("main", "#1bffcc")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize every configuration on startup, tidy up on shutdown.

    Startup is resilient — a failure in one configuration is logged and skipped so it
    cannot prevent the remaining configurations (or the app itself) from coming up.
    """
    config_names = get_available_configs()
    ConsoleMessageStylizer.log(
        f"Starting GFP CoreX. 📋 Available configurations: {len(config_names)}"
    )

    configs_feedback = {"configs": []}

    for config_name in config_names:
        try:
            config = get_config(config_name)

            # Initialize database and Redis, then load plugins for this config.
            db_result = await init_database(config_name, config)
            redis_result = await init_redis(config_name, config)

            from .plugins.manager import plugin_manager
            await plugin_manager.load_all_plugins(config_name)
        except Exception as e:
            ConsoleMessageStylizer.log(
                f"❌ Configuration '{config_name}' failed to initialize: {e}"
            )
            configs_feedback["configs"].append({
                "name": config_name,
                "db": {"status": "error", "message": str(e)},
                "redis": {"status": "error", "message": str(e)},
            })
            continue

        # Surface degraded configurations without aborting startup.
        if db_result["status"] == "error" or redis_result["status"] == "error":
            ConsoleMessageStylizer.log(
                f"⚠️  Configuration '{config_name}' has errors - "
                f"Database: {db_result['status']}, Redis: {redis_result['status']}"
            )
        elif db_result["status"] == "warning" or redis_result["status"] == "warning":
            ConsoleMessageStylizer.log(
                f"⚠️  Configuration '{config_name}' initialized with warnings - "
                f"Database: {db_result['status']}, Redis: {redis_result['status']}"
            )

        configs_feedback["configs"].append({
            "name": config_name,
            "db": db_result,
            "redis": redis_result,
        })

    ConsoleMessageStylizer.log("🎉 GFP CoreX started successfully")
    for entry in configs_feedback["configs"]:
        ConsoleMessageStylizer.log(
            f"----Configuration '{entry['name']}' - "
            f"Database: {entry['db']['status']}, Redis: {entry['redis']['status']}"
        )

    yield

    ConsoleMessageStylizer.log("🛑 Shutting down")
    await close_database()
    await close_redis()
    ConsoleMessageStylizer.log("Shutdown complete")


def _gather_cors_settings() -> Tuple[List[str], bool]:
    """Aggregate CORS allowed origins across all configurations.

    Returns ``(origins, allow_credentials)``. If any configuration allows the ``"*"``
    wildcard, credentials are disabled — browsers reject wildcard-origin responses that
    also carry credentials, so pairing the two silently breaks CORS. Otherwise the union
    of explicit origins is returned with credentials enabled.

    Per-config failures (e.g. an unresolved ``${ENV}`` secret) are logged and skipped so
    a single broken configuration cannot crash the module-level ``app = create_app()``.
    """
    origins = set()
    wildcard = False

    for config_name in get_available_configs():
        try:
            config = get_config(config_name)
        except Exception as e:
            ConsoleMessageStylizer.log(f"⚠️  Skipping CORS for '{config_name}': {e}")
            continue

        for origin in config.app.cors_origins:
            if origin == "*":
                wildcard = True
            else:
                origins.add(origin)

    if wildcard:
        return ["*"], False
    return sorted(origins), True


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="GFP CoreX",
        description="Multi-configuration FastAPI backend with isolated databases",
        version="1.0.0",
        lifespan=lifespan,
        openapi_tags=[
            {
                "name": "Plugin Management",
                "description": "API endpoints for managing plugins (create, update, delete, execute)"
            },
            {
                "name": "Plugin Integration",
                "description": "API endpoints for integrating plugins into other workflows"
            },
            {
                "name": "Authentication",
                "description": "User authentication and authorization endpoints"
            },
            {
                "name": "Configuration",
                "description": "Configuration management endpoints"
            }
        ]
    )

    # Global request-size limit and rate limiting (added first → innermost, so the
    # CORS layer below wraps their rejections and they still carry CORS headers).
    add_security_middleware(app)

    # CORS driven by configuration rather than a blanket wildcard-with-credentials.
    cors_origins, allow_credentials = _gather_cors_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Added last → outermost layer, so it times the full request including CORS
    # handling and rate-limit rejections. Feeds GET /metrics below.
    app.add_middleware(PrometheusMiddleware)

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "message": "GFP CoreX",
            "version": "1.0.0",
            "description": "Multi-configuration FastAPI backend with isolated databases",
            "docs": "/docs",
            "health": "/health"
        }

    # Prometheus scrape endpoint (see core/metrics.py). Excluded from OpenAPI —
    # it is infrastructure, not part of the public API contract.
    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        """Expose collected metrics in Prometheus text exposition format."""
        return Response(content=render_latest(), media_type=PROMETHEUS_CONTENT_TYPE)

    # Global health check
    @app.get("/health")
    async def health_check():
        """Global health check — lightweight connectivity probes only.

        Uses cheap ``SELECT 1`` / Redis ``PING`` checks rather than the heavy
        schema-initializing path, so it is safe to poll frequently.
        """
        config_names = get_available_configs()

        config_statuses = {}
        overall_healthy = True

        for config_name in config_names:
            try:
                config = get_config(config_name)

                db_ok = await ping_database(config_name, config)
                redis_ok = await redis_manager.ping(config_name, config)
                healthy = db_ok and redis_ok

                config_statuses[config_name] = {
                    "database": "healthy" if db_ok else "unhealthy",
                    "redis": "healthy" if redis_ok else "unhealthy",
                    "overall": "healthy" if healthy else "unhealthy",
                }

                if not healthy:
                    overall_healthy = False

            except Exception as e:
                config_statuses[config_name] = {
                    "error": str(e),
                    "overall": "error"
                }
                overall_healthy = False

        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "available_configurations": config_names,
            "total_configurations": len(config_names),
            "configurations_status": config_statuses,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    # Detailed configuration status check
    @app.get("/health/{config_name}")
    async def config_health_check(config_name: str):
        """Check health status of a specific configuration (lightweight)."""
        try:
            config = get_config(config_name)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{config_name}' not found"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid configuration '{config_name}': {str(e)}"
            )

        db_ok = await ping_database(config_name, config)
        redis_ok = await redis_manager.ping(config_name, config)

        return {
            "config_name": config_name,
            "database": "healthy" if db_ok else "unhealthy",
            "redis": "healthy" if redis_ok else "unhealthy",
            "overall_status": "healthy" if db_ok and redis_ok else "unhealthy",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    # Create universal router for all configurations
    from .api.auth import create_universal_auth_router

    # Mount the universal router for authentication and user management
    app.include_router(
        create_universal_auth_router(),
        prefix="/api/c/{config_name}/api/v1"
    )

    # Mount the configuration management router
    app.include_router(
        create_config_router(),
        prefix="/api/v1"
    )

    # Mount the plugin management router for all configurations
    from .api.plugins import create_plugin_router
    app.include_router(
        create_plugin_router(),
        prefix="/api/c/{config_name}/api/v1"
    )

    # Mount the plugin integration router for all configurations
    from .api.plugin_integration import router as plugin_integration_router
    app.include_router(
        plugin_integration_router,
        prefix="/api/c/{config_name}/api/v1/plugin-integration"
    )

    # Universal configuration-specific health check
    @app.get("/api/c/{config_name}/api/v1/health")
    async def config_health(config_name: str):
        """Configuration-specific health check."""
        try:
            config = get_config(config_name)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{config_name}' not found"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid configuration '{config_name}': {str(e)}"
            )

        return {
            "status": "healthy",
            "config": config.app.title,
            "version": config.app.version,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.gfpcorex.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

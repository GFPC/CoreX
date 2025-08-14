"""
Main FastAPI application for GFP CoreX.
Multi-configuration backend with dynamic routing.
"""

import asyncio

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from src.gfpcorex.utils.logging import GFPConsoleMessageStylizer
from .core.config import get_available_configs, get_config
from .core.database import init_database, close_database
from .core.redis_manager import init_redis, close_redis
from .api.config import create_config_router

ConsoleMessageStylizer = GFPConsoleMessageStylizer("main", "#1bffcc")

async def _on_startup() -> None:
    """Application startup tasks without using yield-based lifespan."""
    config_names = get_available_configs()

    ConsoleMessageStylizer.log(f"Starting GFP CoreX. 📋 Available configurations: {len(config_names)}")

    configs_feedack = {
        "configs": []
    }

    # Initialize each configuration
    for config_name in config_names:
        config = get_config(config_name)

        # Initialize database
        db_result = await init_database(config_name, config)

        # Initialize Redis
        redis_result = await init_redis(config_name, config)

        # Load plugins
        from .plugins.manager import plugin_manager
        await plugin_manager.load_all_plugins(config_name)

        # Check overall status for this configuration
        if db_result['status'] == 'error' or redis_result['status'] == 'error':
            ConsoleMessageStylizer.log(f"⚠️  Configuration '{config_name}' has errors - Database: {db_result['status']}, Redis: {redis_result['status']}")
        elif db_result['status'] == 'warning' or redis_result['status'] == 'warning':
            ConsoleMessageStylizer.log(f"⚠️  Configuration '{config_name}' initialized with warnings - Database: {db_result['status']}, Redis: {redis_result['status']}")
        else:
           pass
        configs_feedack["configs"].append({
            "name": config_name,
            "db": db_result,
            "redis": redis_result
        })
    ConsoleMessageStylizer.log("🎉 GFP CoreX started successfully")
    for i in configs_feedack["configs"]:
        ConsoleMessageStylizer.log(f"----Configuration '{i['name']}' - Database: {i['db']['status']}, Redis: {i['redis']['status']}")
    ConsoleMessageStylizer.log(f"ok")


async def _on_shutdown() -> None:
    """Application shutdown tasks without using yield-based lifespan."""
    ConsoleMessageStylizer.log("🛑 Shutting down")
    await close_database()
    await close_redis()
    ConsoleMessageStylizer.log("shutdown successfully")

def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="GFP CoreX",
        description="Multi-configuration FastAPI backend with isolated databases",
        version="1.0.0",
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

    # Register startup/shutdown event handlers
    app.add_event_handler("startup", _on_startup)
    app.add_event_handler("shutdown", _on_shutdown)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
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
    
    # Global health check
    @app.get("/health")
    async def health_check():
        """Global health check endpoint."""
        config_names = get_available_configs()
        
        # Check status of all configurations
        config_statuses = {}
        overall_healthy = True
        
        for config_name in config_names:
            try:
                config = get_config(config_name)
                
                # Quick database check
                db_result = await init_database(config_name, config)
                redis_result = await init_redis(config_name, config)
                
                config_statuses[config_name] = {
                    "database": db_result['status'],
                    "redis": redis_result['status'],
                    "overall": "healthy" if db_result['status'] == 'success' and redis_result['status'] == 'success' else "unhealthy"
                }
                
                if config_statuses[config_name]['overall'] != 'healthy':
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
            "timestamp": "2024-01-13T12:00:00Z"  # You can add real timestamp here
        }
    
    # Detailed configuration status check
    @app.get("/health/{config_name}")
    async def config_health_check(config_name: str):
        """Check health status of specific configuration."""
        try:
            config = get_config(config_name)
            
            # Check database status
            db_result = await init_database(config_name, config)
            
            # Check Redis status
            redis_result = await init_redis(config_name, config)
            
            return {
                "config_name": config_name,
                "database": db_result,
                "redis": redis_result,
                "overall_status": "healthy" if db_result['status'] == 'success' and redis_result['status'] == 'success' else "unhealthy"
            }
        except Exception as e:
            return {
                "config_name": config_name,
                "error": str(e),
                "overall_status": "error"
            }
    
    # Dynamic configuration-specific endpoints
    config_names = get_available_configs()
    
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
            "timestamp": asyncio.get_event_loop().time()
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
        log_level="info",  # Изменено с "info" на "error"
        #access_log=False,    # Отключаем access логи
    )

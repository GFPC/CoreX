"""
Main FastAPI application for GFP CoreX multi-configuration backend.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_available_configs, get_config
from .core.database import close_database, init_database
from .core.redis import close_redis, init_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    Args:
        app: FastAPI application instance
    """
    # Startup
    print("🚀 Starting GFP CoreX Multi-Config API...")
    
    # Initialize all configurations
    available_configs = get_available_configs()
    print(f"📋 Available configurations: {available_configs}")
    
    for config_name in available_configs:
        try:
            config = get_config(config_name)
            print(f"⚙️  Initializing configuration: {config_name}")
            
            # Initialize database
            await init_database(config_name, config)
            
            # Initialize Redis
            await init_redis(config_name, config)
            
            print(f"✅ Configuration '{config_name}' initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize configuration '{config_name}': {e}")
    
    print("🎉 GFP CoreX Multi-Config API started successfully!")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down GFP CoreX Multi-Config API...")
    
    # Close all connections
    await close_database()
    await close_redis()
    
    print("👋 GFP CoreX Multi-Config API shutdown complete!")


def create_app() -> FastAPI:
    """
    Create the main FastAPI application.
    
    Returns:
        FastAPI application instance
    """
    app = FastAPI(
        title="GFP CoreX Multi-Config API",
        version="1.0.0",
        description="Production-ready multi-configuration FastAPI backend",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Configure based on environment
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with available configurations."""
        configs = get_available_configs()
        return {
            "message": "Welcome to GFP CoreX Multi-Config API!",
            "version": "1.0.0",
            "available_configurations": configs,
            "docs": "/docs",
            "redoc": "/redoc",
        }
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Global health check endpoint."""
        configs = get_available_configs()
        return {
            "status": "healthy",
            "available_configurations": configs,
            "total_configurations": len(configs),
        }
    
    # Configuration endpoints
    @app.get("/api/c/{config_name}/api/v1/health")
    async def config_health_check(config_name: str):
        """Health check for specific configuration."""
        try:
            config = get_config(config_name)
            return {
                "status": "healthy",
                "config": config.app.title,
                "version": config.app.version,
                "timestamp": asyncio.get_event_loop().time(),
            }
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Configuration '{config_name}' not found")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid configuration: {e}")
    
    @app.get("/api/c/{config_name}/api/v1/example")
    async def config_example(config_name: str):
        """Example endpoint for specific configuration."""
        try:
            config = get_config(config_name)
            return {
                "message": "Hello from GFP CoreX!",
                "config": config.app.title,
                "database_url": config.db.url.split("@")[1] if "@" in config.db.url else "hidden",
                "redis_url": config.redis.url.split("@")[1] if "@" in config.redis.url else "hidden",
            }
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Configuration '{config_name}' not found")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid configuration: {e}")
    
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

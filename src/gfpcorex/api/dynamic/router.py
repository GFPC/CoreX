"""
Dynamic router for multi-configuration FastAPI backend.
Handles URL pattern: /api/c/{config_name}/api/v1/...
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import Config, get_config, get_available_configs
from ...core.database import get_db_session
from ...core.redis import get_redis_client
from redis.asyncio import Redis


class DynamicRouter:
    """Manages dynamic routing for different configurations."""
    
    def __init__(self):
        self._config_routers: Dict[str, APIRouter] = {}
        self._config_apps: Dict[str, FastAPI] = {}
    
    def get_config_router(self, config_name: str) -> APIRouter:
        """
        Get or create router for configuration.
        
        Args:
            config_name: Name of the configuration
            
        Returns:
            APIRouter instance
        """
        if config_name not in self._config_routers:
            router = APIRouter(prefix=f"/api/c/{config_name}/api/v1")
            self._config_routers[config_name] = router
        return self._config_routers[config_name]
    
    def get_config_app(self, config_name: str, config: Config) -> FastAPI:
        """
        Get or create FastAPI app for configuration.
        
        Args:
            config_name: Name of the configuration
            config: Configuration object
            
        Returns:
            FastAPI instance
        """
        if config_name not in self._config_apps:
            app = FastAPI(
                title=config.app.title,
                version=config.app.version,
                debug=config.app.debug,
            )
            
            # Add CORS middleware
            app.add_middleware(
                CORSMiddleware,
                allow_origins=config.app.cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            
            # Include the router
            router = self.get_config_router(config_name)
            app.include_router(router)
            
            self._config_apps[config_name] = app
        
        return self._config_apps[config_name]


# Global dynamic router instance
dynamic_router = DynamicRouter()


async def get_config_dependencies(config_name: str) -> tuple[Config, AsyncSession, Redis]:
    """
    Get dependencies for a specific configuration.
    
    Args:
        config_name: Name of the configuration
        
    Returns:
        Tuple of (config, db_session, redis_client)
    """
    try:
        config = get_config(config_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Configuration '{config_name}' not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid configuration: {e}")
    
    # Get database session
    db_session = get_db_session(config_name, config)
    db = await anext(db_session)
    
    # Get Redis client
    redis_session = get_redis_client(config_name, config)
    redis_client = await anext(redis_session)
    
    return config, db, redis_client


def create_dynamic_app() -> FastAPI:
    """
    Create the main FastAPI application with dynamic routing.
    
    Returns:
        FastAPI instance
    """
    app = FastAPI(
        title="GFP CoreX Multi-Config API",
        version="1.0.0",
        description="Production-ready multi-configuration FastAPI backend",
    )
    
    # Add CORS middleware for the main app
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Configure based on environment
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount dynamic routers
    for config_name in get_available_configs():
        try:
            config = get_config(config_name)
            config_app = dynamic_router.get_config_app(config_name, config)
            
            # Mount the config app
            app.mount(f"/api/c/{config_name}", config_app)
            
        except Exception as e:
            print(f"Warning: Failed to mount config '{config_name}': {e}")
    
    return app


# Health check endpoint for each configuration
@dynamic_router.get_config_router("health").get("/health")
async def health_check(
    request: Request,
    config: Config = Depends(lambda: get_config_dependencies("health")[0]),
    db: AsyncSession = Depends(lambda: get_config_dependencies("health")[1]),
    redis: Redis = Depends(lambda: get_config_dependencies("health")[2]),
):
    """
    Health check endpoint for each configuration.
    
    Returns:
        Health status information
    """
    return {
        "status": "healthy",
        "config": config.app.title,
        "version": config.app.version,
        "timestamp": asyncio.get_event_loop().time(),
    }


# Example endpoint for each configuration
@dynamic_router.get_config_router("example").get("/example")
async def example_endpoint(
    request: Request,
    config: Config = Depends(lambda: get_config_dependencies("example")[0]),
    db: AsyncSession = Depends(lambda: get_config_dependencies("example")[1]),
    redis: Redis = Depends(lambda: get_config_dependencies("example")[2]),
):
    """
    Example endpoint for each configuration.
    
    Returns:
        Example response with configuration info
    """
    return {
        "message": "Hello from GFP CoreX!",
        "config": config.app.title,
        "database_url": config.db.url.split("@")[1] if "@" in config.db.url else "hidden",
        "redis_url": config.redis.url.split("@")[1] if "@" in config.redis.url else "hidden",
    } 
"""
Redis management for multi-configuration FastAPI backend.
Supports isolated Redis connections for different configurations.

Usage Examples:
    
    # Option 1: Get Redis client directly
    redis_client = await get_redis_client("dev", config)
    await redis_client.set("key", "value")
    value = await redis_client.get("key")
    
    # Option 2: Use Redis manager directly
    redis_client = redis_manager.get_redis_client("dev", config)
    await redis_client.set("key", "value")
    value = await redis_client.get("key")
    
    # Note: Redis clients are shared and managed automatically.
    # No need to close them manually.
"""

import asyncio
from typing import Dict, Optional

import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Redis

from .config import Config
from ..utils.logging import GFPConsoleMessageStylizer

ConsoleMessageStylizer = GFPConsoleMessageStylizer("redis", "#cc0066")


class RedisManager:
    """Manages Redis connections for different configurations."""
    
    def __init__(self):
        self._pools: Dict[str, ConnectionPool] = {}
        self._clients: Dict[str, Redis] = {}
    
    def get_pool(self, config_name: str, config: Config) -> ConnectionPool:
        """
        Get or create Redis connection pool for configuration.
        
        Args:
            config_name: Name of the configuration
            config: Configuration object
            
        Returns:
            ConnectionPool instance
        """
        if config_name not in self._pools:
            # Parse Redis URL to get connection details
            url = config.redis.url
            pool = redis.ConnectionPool.from_url(
                url,
                max_connections=config.redis.pool_size,
                decode_responses=config.redis.decode_responses,
            )
            self._pools[config_name] = pool
        
        return self._pools[config_name]
    
    def get_client(self, config_name: str, config: Config) -> Redis:
        """
        Get or create Redis client for configuration.
        
        Args:
            config_name: Name of the configuration
            config: Configuration object
            
        Returns:
            Redis client instance
        """
        if config_name not in self._clients:
            pool = self.get_pool(config_name, config)
            client = redis.Redis(connection_pool=pool)
            self._clients[config_name] = client
        
        return self._clients[config_name]
    
    def get_redis_client(self, config_name: str, config: Config) -> Redis:
        """
        Get Redis client for configuration.
        
        Args:
            config_name: Name of the configuration
            config: Configuration object
            
        Returns:
            Redis client instance
            
        Note:
            This method returns a Redis client that is shared across the application.
            No need to close it manually as it's managed by the RedisManager.
        """
        return self.get_client(config_name, config)
    
    async def ping(self, config_name: str, config: Config) -> bool:
        """
        Ping Redis server for configuration.
        
        Args:
            config_name: Name of the configuration
            config: Configuration object
            
        Returns:
            True if connection is successful
        """
        try:
            client = self.get_client(config_name, config)
            await client.ping()
            return True
        except Exception:
            return False
    
    async def close_all(self) -> None:
        """Close all Redis connections."""
        for client in self._clients.values():
            await client.close()
        for pool in self._pools.values():
            await pool.disconnect()
        self._clients.clear()
        self._pools.clear()


# Global Redis manager instance
redis_manager = RedisManager()


async def get_redis_client(config_name: str, config: Config) -> Redis:
    """
    Dependency for getting Redis client.
    
    Args:
        config_name: Name of the configuration
        config: Configuration object
        
    Returns:
        Redis client instance
        
    Note:
        This function returns a Redis client that is shared across the application.
        No need to close it manually as it's managed by the RedisManager.
    """
    return redis_manager.get_redis_client(config_name, config)


async def init_redis(config_name: str, config: Config) -> dict:
    """
    Initialize Redis connection for configuration.
    
    Args:
        config_name: Name of the configuration
        config: Configuration object
        
    Returns:
        dict: {"status": "success"|"warning"|"error", "message": str}
    """
    try:
        is_connected = await redis_manager.ping(config_name, config)
        if not is_connected:
            return {
                "status": "warning",
                "message": f"Failed to connect to Redis for {config_name}"
            }
        else:
            return {
                "status": "success",
                "message": f"Redis connection successful for {config_name}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Redis connection failed for {config_name}: {e}"
        }


async def close_redis() -> None:
    """Close all Redis connections."""
    await redis_manager.close_all()


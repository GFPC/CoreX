"""
Redis management for multi-configuration FastAPI backend.
Supports isolated Redis connections for different configurations.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Optional

import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Redis

from .config import Config


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
    
    @asynccontextmanager
    async def get_redis(self, config_name: str, config: Config) -> AsyncGenerator[Redis, None]:
        """
        Get Redis client for configuration.
        
        Args:
            config_name: Name of the configuration
            config: Configuration object
            
        Yields:
            Redis client instance
        """
        client = self.get_client(config_name, config)
        try:
            yield client
        finally:
            # Don't close the client as it's shared
            pass
    
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


async def get_redis_client(config_name: str, config: Config) -> AsyncGenerator[Redis, None]:
    """
    Dependency for getting Redis client.
    
    Args:
        config_name: Name of the configuration
        config: Configuration object
        
    Yields:
        Redis client instance
    """
    async with redis_manager.get_redis(config_name, config) as client:
        yield client


async def init_redis(config_name: str, config: Config) -> None:
    """
    Initialize Redis connection for configuration.
    
    Args:
        config_name: Name of the configuration
        config: Configuration object
    """
    try:
        is_connected = await redis_manager.ping(config_name, config)
        if not is_connected:
            print(f"Warning: Failed to connect to Redis for {config_name}")
    except Exception as e:
        print(f"Warning: Redis connection failed for {config_name}: {e}")


async def close_redis() -> None:
    """Close all Redis connections."""
    await redis_manager.close_all()


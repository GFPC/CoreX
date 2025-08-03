"""
Database management for multi-configuration FastAPI backend.
Supports isolated database connections for different configurations.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Optional

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import Config


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class DatabaseManager:
    """Manages database connections for different configurations."""
    
    def __init__(self):
        self._engines: Dict[str, AsyncEngine] = {}
        self._sessionmakers: Dict[str, async_sessionmaker[AsyncSession]] = {}
        self._metadata = MetaData()
    
    def get_engine(self, config_name: str, config: Config) -> AsyncEngine:
        """
        Get or create database engine for configuration.
        
        Args:
            config_name: Name of the configuration
            config: Configuration object
            
        Returns:
            AsyncEngine instance
        """
        if config_name not in self._engines:
            engine = create_async_engine(
                config.db.url,
                pool_size=config.db.pool_size,
                max_overflow=config.db.max_overflow,
                pool_pre_ping=config.db.pool_pre_ping,
                echo=config.db.echo,
            )
            self._engines[config_name] = engine
        
        return self._engines[config_name]
    
    def get_sessionmaker(self, config_name: str, config: Config) -> async_sessionmaker[AsyncSession]:
        """
        Get or create session maker for configuration.
        
        Args:
            config_name: Name of the configuration
            config: Configuration object
            
        Returns:
            AsyncSessionMaker instance
        """
        if config_name not in self._sessionmakers:
            engine = self.get_engine(config_name, config)
            sessionmaker = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            self._sessionmakers[config_name] = sessionmaker
        
        return self._sessionmakers[config_name]
    
    @asynccontextmanager
    async def get_session(self, config_name: str, config: Config) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session for configuration.
        
        Args:
            config_name: Name of the configuration
            config: Configuration object
            
        Yields:
            AsyncSession instance
        """
        sessionmaker = self.get_sessionmaker(config_name, config)
        async with sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def create_tables(self, config_name: str, config: Config) -> None:
        """
        Create all tables for configuration.
        
        Args:
            config_name: Name of the configuration
            config: Configuration object
        """
        engine = self.get_engine(config_name, config)
        async with engine.begin() as conn:
            await conn.run_sync(self._metadata.create_all)
    
    async def drop_tables(self, config_name: str, config: Config) -> None:
        """
        Drop all tables for configuration.
        
        Args:
            config_name: Name of the configuration
            config: Configuration object
        """
        engine = self.get_engine(config_name, config)
        async with engine.begin() as conn:
            await conn.run_sync(self._metadata.drop_all)
    
    async def close_all(self) -> None:
        """Close all database engines."""
        for engine in self._engines.values():
            await engine.dispose()
        self._engines.clear()
        self._sessionmakers.clear()
    
    def get_metadata(self) -> MetaData:
        """Get database metadata."""
        return self._metadata


# Global database manager instance
db_manager = DatabaseManager()


async def get_db_session(config_name: str, config: Config) -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session.
    
    Args:
        config_name: Name of the configuration
        config: Configuration object
        
    Yields:
        AsyncSession instance
    """
    async with db_manager.get_session(config_name, config) as session:
        yield session


async def init_database(config_name: str, config: Config) -> None:
    """
    Initialize database for configuration.
    
    Args:
        config_name: Name of the configuration
        config: Configuration object
    """
    try:
        await db_manager.create_tables(config_name, config)
    except Exception as e:
        # Log error but don't fail startup
        print(f"Warning: Failed to create tables for {config_name}: {e}")


async def close_database() -> None:
    """Close all database connections."""
    await db_manager.close_all()


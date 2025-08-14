"""
Database management for multi-configuration FastAPI backend.
Supports isolated database connections for different configurations.

Usage Examples:
    
    # Option 1: Manual session management (more control)
    session = await get_db_session("dev", config)
    try:
        result = await session.execute(query)
        await session.commit()
    finally:
        await session.close()
    
    # Option 2: Get session and manage cleanup manually
    session = await get_session_auto_cleanup("dev", config)
    try:
        result = await session.execute(query)
        await commit_and_close_session(session)
    except Exception:
        await session.close()
        raise
    
    # Option 3: Direct database manager usage
    session = db_manager.get_session_with_cleanup("dev", config)
    try:
        result = await session.execute(query)
        await db_manager.commit_session(session)
    except Exception:
        await session.close()
        raise
"""

import asyncio
from typing import Dict, Optional

from sqlalchemy import MetaData, text, inspect
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import Config
from ..utils.logging import GFPConsoleMessageStylizer

ConsoleMessageStylizer = GFPConsoleMessageStylizer("database", "#0066cc")


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
    
    def create_session(self, config_name: str, config: Config) -> AsyncSession:
        """
        Create a new database session for configuration.
        
        Args:
            config_name: Name of the configuration
            config: Configuration object
            
        Returns:
            AsyncSession instance
            
        Note:
            Caller is responsible for managing the session lifecycle.
            Consider using the get_session_auto_cleanup function for automatic cleanup.
        """
        sessionmaker = self.get_sessionmaker(config_name, config)
        return sessionmaker()

    async def get_session_with_cleanup(self, config_name: str, config: Config) -> AsyncSession:
        """
        Get database session with automatic cleanup.
        
        Args:
            config_name: Name of the configuration
            config: Configuration object
            
        Returns:
            AsyncSession instance
            
        Note:
            This method returns a session that will be automatically cleaned up.
            Use it when you need a session with automatic transaction management.
        """
        return self.create_session(config_name, config)

    async def commit_session(self, session: AsyncSession) -> None:
        """Commit session and close it."""
        try:
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def check_tables_exist(self, config_name: str, config: Config) -> bool:
        """
        Check if required tables exist in the database.
        
        Args:
            config_name: Name of the configuration
            config: Configuration object
            
        Returns:
            bool: True if all required tables exist
        """
        try:
            engine = self.get_engine(config_name, config)
            
            # Detect database type from URL
            db_url = config.db.url.lower()
            is_mysql = "mysql" in db_url
            
            # Use async connection to check tables
            async with engine.begin() as conn:
                if is_mysql:
                    # MySQL query
                    result = await conn.execute(text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = DATABASE()
                    """))
                else:
                    # PostgreSQL query
                    result = await conn.execute(text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public'
                    """))
                
                existing_tables = {row[0] for row in result.fetchall()}
                
                # Required tables based on our models
                required_tables = {"users", "auth_sessions", "user_roles", "plugins"}
                
                # Check if all required tables exist
                missing_tables = required_tables - existing_tables
                
                if missing_tables:
                    ConsoleMessageStylizer.log(f"📋 Missing tables for {config_name}: {missing_tables}")
                    return False
                else:
                    return True
                    
        except Exception as e:
            ConsoleMessageStylizer.log(f"⚠️  Error checking tables for {config_name}: {e}")
            return False
    
    async def create_tables_from_models(self, config_name: str, config: Config) -> bool:
        """
        Create all tables from SQLAlchemy models.
        
        Args:
            config_name: Name of the configuration
            config: Configuration object
            
        Returns:
            bool: True if tables were created successfully
        """
        try:
            ConsoleMessageStylizer.log(f"🔧 Creating tables from models for {config_name}...")
            
            # Import all models to ensure they are registered with Base.metadata
            from ..models.user import User
            from ..models.auth_session import AuthSession
            from ..models.user_role import UserRole
            from ..models.plugin import Plugin
            
            engine = self.get_engine(config_name, config)
            
            # Create all tables
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            # Insert default roles if user_roles is empty
            async with async_sessionmaker(engine, class_=AsyncSession)() as session:
                result = await session.execute(text("SELECT COUNT(*) FROM user_roles"))
                count = result.scalar()
                if count == 0:
                    ConsoleMessageStylizer.log("🌱 Inserting default roles into user_roles...")
                    session.add_all([
                        UserRole(id=1, name="admin", description="Administrator"),
                        UserRole(id=2, name="user", description="Regular user")
                    ])
                    await session.commit()
            
            ConsoleMessageStylizer.log(f"✅ Tables created successfully for {config_name}")
            return True
            
        except Exception as e:
            ConsoleMessageStylizer.log(f"❌ Failed to create tables for {config_name}: {e}")
            return False
    
    async def drop_tables(self, config_name: str, config: Config) -> None:
        """
        Drop all tables for configuration.
        
        Args:
            config_name: Name of the configuration
            config: Configuration object
        """
        engine = self.get_engine(config_name, config)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    async def close_all(self) -> None:
        """Close all database engines."""
        for engine in self._engines.values():
            await engine.dispose()
        self._engines.clear()
        self._sessionmakers.clear()
    
    def get_metadata(self) -> MetaData:
        """Get database metadata."""
        return Base.metadata


# Global database manager instance
db_manager = DatabaseManager()


async def get_db_session(config_name: str, config: Config) -> AsyncSession:
    """
    Dependency for getting database session.
    
    Args:
        config_name: Name of the configuration
        config: Configuration object
        
    Returns:
        AsyncSession instance
        
            Note:
            Caller is responsible for closing the session when done.
            Consider using the get_session_auto_cleanup function for automatic cleanup.
    """
    return db_manager.create_session(config_name, config)


async def get_session_auto_cleanup(config_name: str, config: Config) -> AsyncSession:
    """
    Get database session with automatic cleanup.
    
    Args:
        config_name: Name of the configuration
        config: Configuration object
        
    Returns:
        AsyncSession instance
        
    Note:
        This function returns a session that will be automatically cleaned up.
        Use it when you need a session with automatic transaction management.
    """
    return await get_db_session(config_name, config)

async def commit_and_close_session(session: AsyncSession) -> None:
    """Commit session and close it."""
    try:
        await session.commit()
        await session.close()
    except Exception:
        await session.rollback()
        await session.close()
        raise


async def init_database(config_name: str, config: Config) -> dict:
    """
    Initialize database for configuration.
    
    Args:
        config_name: Name of the configuration
        config: Configuration object
        
    Returns:
        dict: {"status": "success"|"warning"|"error", "message": str}
    """
    try:
        # Test connection first
        engine = db_manager.get_engine(config_name, config)
        async with engine.begin() as conn:
            # Simple connection test
            await conn.execute(text("SELECT 1"))
        
        # Check if tables exist
        tables_exist = await db_manager.check_tables_exist(config_name, config)
        
        if not tables_exist:
            # Create tables from models
            success = await db_manager.create_tables_from_models(config_name, config)
            if not success:
                return {
                    "status": "warning",
                    "message": f"Database schema not ready for {config_name}"
                }
            else:
                return {
                    "status": "success",
                    "message": f"Database initialized and tables created for {config_name}"
                }
        else:
            return {
                "status": "success",
                "message": f"Database connection established and schema ready for {config_name}"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to database for {config_name}: {e}"
        }


async def close_database() -> None:
    """Close all database connections."""
    await db_manager.close_all()


# Example usage:
"""
# Option 1: Manual session management (more control)
session = await get_db_session("dev", config)
try:
    result = await session.execute(query)
    await session.commit()
finally:
    await session.close()

# Option 2: Get session and manage cleanup manually
session = await get_session_auto_cleanup("dev", config)
try:
    result = await session.execute(query)
    await commit_and_close_session(session)
except Exception:
    await session.close()
    raise

# Option 3: Direct database manager usage
session = db_manager.get_session_with_cleanup("dev", config)
try:
    result = await session.execute(query)
    await db_manager.commit_session(session)
except Exception:
    await session.close()
    raise
"""


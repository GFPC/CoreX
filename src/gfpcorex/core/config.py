"""
Configuration management for multi-configuration FastAPI backend.
Supports dynamic loading of configurations from YAML files.
"""

from pathlib import Path
from typing import Dict, List

import yaml
from pydantic import BaseModel, Field, field_validator


class DatabaseConfig(BaseModel):
    """Database configuration settings."""
    url: str = Field(..., description="Database connection URL")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Maximum overflow connections")
    pool_pre_ping: bool = Field(default=True, description="Enable connection health checks")
    echo: bool = Field(default=False, description="Enable SQL logging")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate database URL format."""
        # Поддержка всех популярных баз данных
        supported_drivers = [
            "postgresql+asyncpg://",    # PostgreSQL
            "mysql+aiomysql://",        # MySQL
            "mariadb+aiomysql://",      # MariaDB
            "sqlite+aiosqlite://",      # SQLite
            "oracle+asyncoracle://",    # Oracle
            "mssql+asyncmssql://",      # SQL Server
            "cockroachdb+asyncpg://",   # CockroachDB
            "redis://",                 # Redis как БД
        ]

        if not any(v.startswith(driver) for driver in supported_drivers):
            raise ValueError(f"Database URL must use one of supported async drivers: {', '.join(supported_drivers)}")
        return v
    
    def get_database_name(self) -> str:
        """Extract database name from URL."""
        try:
            # Parse URL to get database name
            if "postgresql" in self.url or "mysql" in self.url or "mariadb" in self.url:
                # Format: driver://user:pass@host:port/db_name
                parts = self.url.split("/")
                if len(parts) >= 4:
                    db_part = parts[-1]
                    # Remove query parameters if any
                    db_name = db_part.split("?")[0]
                    return db_name
            elif "sqlite" in self.url:
                # Format: sqlite+aiosqlite:///path/to/database.db
                parts = self.url.split("/")
                if len(parts) >= 4:
                    return parts[-1]
            return "unknown"
        except Exception:
            return "unknown"


class RedisConfig(BaseModel):
    """Redis configuration settings."""
    url: str = Field(..., description="Redis connection URL")
    pool_size: int = Field(default=10, description="Connection pool size")
    decode_responses: bool = Field(default=True, description="Decode responses to strings")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate Redis URL format."""
        if not v.startswith("redis://"):
            raise ValueError("Redis URL must start with redis://")
        return v


class AuthConfig(BaseModel):
    """Authentication configuration settings."""
    secret_key: str = Field(..., description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiry")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiry")

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key length."""
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v


class AppConfig(BaseModel):
    """Application configuration settings."""
    title: str = Field(default="GFP CoreX", description="Application title")
    version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    cors_origins: List[str] = Field(default=[], description="CORS allowed origins")


class LoggingConfig(BaseModel):
    """Logging configuration settings."""
    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(default="text", description="Log format (text/json)")
    handlers: List[str] = Field(default=["console"], description="Log handlers")


class SecurityConfig(BaseModel):
    """Security configuration settings."""
    bcrypt_rounds: int = Field(default=12, description="BCrypt rounds")
    rate_limit_per_minute: int = Field(default=100, description="Rate limit per minute")
    max_request_size: str = Field(default="10MB", description="Maximum request size")


class Config(BaseModel):
    """Complete configuration model."""
    db: DatabaseConfig
    redis: RedisConfig
    auth: AuthConfig
    app: AppConfig
    logging: LoggingConfig
    security: SecurityConfig


class ConfigManager:
    """Manages dynamic configuration loading and caching."""
    
    def __init__(self, configs_dir: str = "configs"):
        self.configs_dir = Path(configs_dir)
        self._configs_cache: Dict[str, Config] = {}
        self._ensure_configs_dir()
    
    def _ensure_configs_dir(self) -> None:
        """Ensure configs directory exists."""
        self.configs_dir.mkdir(exist_ok=True)
    
    def load_config(self, config_name: str) -> Config:
        """
        Load configuration by name.
        
        Args:
            config_name: Name of the configuration (e.g., 'prod', 'dev')
            
        Returns:
            Config object with loaded settings
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        # Check cache first
        if config_name in self._configs_cache:
            return self._configs_cache[config_name]
        
        # Load from file
        config_file = self.configs_dir / f"{config_name}.yaml"
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
            
            # Validate and create config
            config = Config(**config_data)
            
            # Cache the config
            self._configs_cache[config_name] = config
            
            return config
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load config '{config_name}': {e}")
    
    def create_config(self, config_name: str, config_data: dict) -> Config:
        """
        Create a new configuration dynamically.
        
        Args:
            config_name: Name of the new configuration
            config_data: Configuration data dictionary
            
        Returns:
            Config object with created settings
            
        Raises:
            ValueError: If config is invalid or already exists
        """
        # Check if config already exists
        config_file = self.configs_dir / f"{config_name}.yaml"
        if config_file.exists():
            raise ValueError(f"Configuration '{config_name}' already exists")
        
        try:
            # Validate config data
            config = Config(**config_data)
            
            # Save to file
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            
            # Cache the config
            self._configs_cache[config_name] = config
            
            return config
            
        except Exception as e:
            raise ValueError(f"Failed to create config '{config_name}': {e}")
    
    def update_config(self, config_name: str, config_data: dict) -> Config:
        """
        Update an existing configuration.
        
        Args:
            config_name: Name of the configuration to update
            config_data: New configuration data dictionary
            
        Returns:
            Config object with updated settings
            
        Raises:
            FileNotFoundError: If config doesn't exist
            ValueError: If config is invalid
        """
        config_file = self.configs_dir / f"{config_name}.yaml"
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration '{config_name}' not found")
        
        try:
            # Validate config data
            config = Config(**config_data)
            
            # Save to file
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            
            # Update cache
            self._configs_cache[config_name] = config
            
            return config
            
        except Exception as e:
            raise ValueError(f"Failed to update config '{config_name}': {e}")
    
    def delete_config(self, config_name: str) -> bool:
        """
        Delete a configuration.
        
        Args:
            config_name: Name of the configuration to delete
            
        Returns:
            True if deleted successfully
            
        Raises:
            FileNotFoundError: If config doesn't exist
        """
        config_file = self.configs_dir / f"{config_name}.yaml"
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration '{config_name}' not found")
        
        try:
            # Remove file
            config_file.unlink()
            
            # Remove from cache
            if config_name in self._configs_cache:
                del self._configs_cache[config_name]
            
            return True
            
        except Exception as e:
            raise ValueError(f"Failed to delete config '{config_name}': {e}")
    
    def get_available_configs(self) -> List[str]:
        """Get list of available configuration names."""
        configs = []
        for file_path in self.configs_dir.glob("*.yaml"):
            configs.append(file_path.stem)
        return configs
    
    def reload_config(self, config_name: str) -> Config:
        """Reload configuration and clear cache."""
        if config_name in self._configs_cache:
            del self._configs_cache[config_name]
        return self.load_config(config_name)
    
    def clear_cache(self) -> None:
        """Clear configuration cache."""
        self._configs_cache.clear()
    
    def get_config_info(self, config_name: str) -> dict:
        """
        Get configuration information without loading full config.
        
        Args:
            config_name: Name of the configuration
            
        Returns:
            Dictionary with config info (name, database, redis, etc.)
        """
        try:
            config = self.load_config(config_name)
            return {
                "name": config_name,
                "database": {
                    "url": config.db.url,
                    "database_name": config.db.get_database_name(),
                    "pool_size": config.db.pool_size
                },
                "redis": {
                    "url": config.redis.url,
                    "pool_size": config.redis.pool_size
                },
                "app": {
                    "title": config.app.title,
                    "version": config.app.version,
                    "debug": config.app.debug
                }
            }
        except Exception as e:
            return {
                "name": config_name,
                "error": str(e)
            }


# Global config manager instance
config_manager = ConfigManager()


def get_config(config_name: str) -> Config:
    """
    Get configuration by name.
    
    Args:
        config_name: Name of the configuration
        
    Returns:
        Config object
    """
    return config_manager.load_config(config_name)


def get_available_configs() -> List[str]:
    """Get list of available configurations."""
    return config_manager.get_available_configs()


def create_config(config_name: str, config_data: dict) -> Config:
    """
    Create a new configuration dynamically.
    
    Args:
        config_name: Name of the new configuration
        config_data: Configuration data dictionary
        
    Returns:
        Config object with created settings
    """
    return config_manager.create_config(config_name, config_data)


def update_config(config_name: str, config_data: dict) -> Config:
    """
    Update an existing configuration.
    
    Args:
        config_name: Name of the configuration to update
        config_data: New configuration data dictionary
        
    Returns:
        Config object with updated settings
    """
    return config_manager.update_config(config_name, config_data)


def delete_config(config_name: str) -> bool:
    """
    Delete a configuration.
    
    Args:
        config_name: Name of the configuration to delete
        
    Returns:
        True if deleted successfully
    """
    return config_manager.delete_config(config_name)


def get_config_info(config_name: str) -> dict:
    """
    Get configuration information.
    
    Args:
        config_name: Name of the configuration
        
    Returns:
        Dictionary with config info
    """
    return config_manager.get_config_info(config_name)


def reload_config(config_name: str) -> Config:
    """
    Reload configuration from file.
    
    Args:
        config_name: Name of the configuration
        
    Returns:
        Config object
    """
    return config_manager.reload_config(config_name)


def clear_config_cache() -> None:
    """Clear configuration cache."""
    config_manager.clear_cache()


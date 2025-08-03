"""
Configuration management for multi-configuration FastAPI backend.
Supports dynamic loading of configurations from YAML files.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseModel):
    """Database configuration settings."""
    url: str = Field(..., description="Database connection URL")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Maximum overflow connections")
    pool_pre_ping: bool = Field(default=True, description="Enable connection health checks")
    echo: bool = Field(default=False, description="Enable SQL logging")

    @validator("url")
    def validate_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v.startswith(("postgresql+asyncpg://", "sqlite+aiosqlite://")):
            raise ValueError("Database URL must use async driver")
        return v


class RedisConfig(BaseModel):
    """Redis configuration settings."""
    url: str = Field(..., description="Redis connection URL")
    pool_size: int = Field(default=10, description="Connection pool size")
    decode_responses: bool = Field(default=True, description="Decode responses to strings")

    @validator("url")
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

    @validator("secret_key")
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


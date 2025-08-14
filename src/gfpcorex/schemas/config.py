"""
Configuration management schemas for GFP CoreX API.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, validator
import re


class DatabaseConfigCreate(BaseModel):
    """Schema for creating database configuration."""
    url: str = Field(..., description="Database connection URL")
    pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(default=20, ge=0, le=100, description="Maximum overflow connections")
    pool_pre_ping: bool = Field(default=True, description="Enable connection health checks")
    echo: bool = Field(default=False, description="Enable SQL logging")

    @validator("url")
    def validate_url(cls, v: str) -> str:
        """Validate database URL format."""
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


class RedisConfigCreate(BaseModel):
    """Schema for creating Redis configuration."""
    url: str = Field(..., description="Redis connection URL")
    pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
    decode_responses: bool = Field(default=True, description="Decode responses to strings")

    @validator("url")
    def validate_url(cls, v: str) -> str:
        """Validate Redis URL format."""
        if not v.startswith("redis://"):
            raise ValueError("Redis URL must start with redis://")
        return v


class AuthConfigCreate(BaseModel):
    """Schema for creating authentication configuration."""
    secret_key: str = Field(..., min_length=32, description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440, description="Access token expiry")
    refresh_token_expire_days: int = Field(default=7, ge=1, le=365, description="Refresh token expiry")


class AppConfigCreate(BaseModel):
    """Schema for creating application configuration."""
    title: str = Field(..., min_length=1, max_length=100, description="Application title")
    version: str = Field(..., description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    cors_origins: List[str] = Field(default=[], description="CORS allowed origins")


class LoggingConfigCreate(BaseModel):
    """Schema for creating logging configuration."""
    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(default="text", description="Log format (text/json)")
    handlers: List[str] = Field(default=["console"], description="Log handlers")


class SecurityConfigCreate(BaseModel):
    """Schema for creating security configuration."""
    bcrypt_rounds: int = Field(default=12, ge=4, le=20, description="BCrypt rounds")
    rate_limit_per_minute: int = Field(default=100, ge=1, le=10000, description="Rate limit per minute")
    max_request_size: str = Field(default="10MB", description="Maximum request size")


class ConfigCreate(BaseModel):
    """Schema for creating a complete configuration."""
    db: DatabaseConfigCreate
    redis: RedisConfigCreate
    auth: AuthConfigCreate
    app: AppConfigCreate
    logging: LoggingConfigCreate = Field(default_factory=LoggingConfigCreate)
    security: SecurityConfigCreate = Field(default_factory=SecurityConfigCreate)


class ConfigUpdate(BaseModel):
    """Schema for updating configuration (all fields optional)."""
    db: Optional[DatabaseConfigCreate] = None
    redis: Optional[RedisConfigCreate] = None
    auth: Optional[AuthConfigCreate] = None
    app: Optional[AppConfigCreate] = None
    logging: Optional[LoggingConfigCreate] = None
    security: Optional[SecurityConfigCreate] = None


class ConfigInfo(BaseModel):
    """Schema for configuration information response."""
    name: str
    database: dict
    redis: dict
    app: dict
    error: Optional[str] = None


class ConfigList(BaseModel):
    """Schema for configuration list response."""
    configs: List[ConfigInfo]
    total: int


class ConfigResponse(BaseModel):
    """Schema for configuration response."""
    name: str
    config: ConfigCreate
    created: bool = True 
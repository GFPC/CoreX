"""
Unit tests for GFP CoreX ConfigManager and Pydantic validation schemas.
"""

import pytest
import tempfile
from pathlib import Path
from src.gfpcorex.core.config import ConfigManager, Config, DatabaseConfig, AuthConfig, RedisConfig


@pytest.fixture
def temp_config_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_database_config_validation():
    valid_db = DatabaseConfig(url="sqlite+aiosqlite:///test.db")
    assert valid_db.get_database_name() == "test.db"

    with pytest.raises(ValueError, match="Database URL must use one of supported async drivers"):
        DatabaseConfig(url="invalid_driver://localhost/db")


def test_auth_config_validation():
    valid_auth = AuthConfig(secret_key="a" * 32)
    assert valid_auth.secret_key == "a" * 32

    with pytest.raises(ValueError, match="Secret key must be at least 32 characters long"):
        AuthConfig(secret_key="short_key")


def test_redis_config_validation():
    valid_redis = RedisConfig(url="redis://localhost:6379/0")
    assert valid_redis.url == "redis://localhost:6379/0"

    with pytest.raises(ValueError, match="Redis URL must start with redis://"):
        RedisConfig(url="http://localhost:6379")


def test_config_manager_create_and_load(temp_config_dir):
    manager = ConfigManager(configs_dir=str(temp_config_dir))

    sample_config_data = {
        "db": {"url": "sqlite+aiosqlite:///test.db"},
        "redis": {"url": "redis://localhost:6379/0"},
        "auth": {"secret_key": "supersecretkey_mustbe32charslong_12345"},
        "app": {"title": "Test App", "version": "1.0.0", "debug": True, "cors_origins": ["*"]},
        "logging": {"level": "DEBUG", "format": "json", "handlers": ["console"]},
        "security": {"bcrypt_rounds": 12, "rate_limit_per_minute": 100, "max_request_size": "10MB"}
    }

    # Create config
    cfg = manager.create_config("test_env", sample_config_data)
    assert cfg.app.title == "Test App"

    # List configs
    available = manager.get_available_configs()
    assert "test_env" in available

    # Load config
    loaded_cfg = manager.load_config("test_env")
    assert loaded_cfg.app.title == "Test App"

    # Get config info
    info = manager.get_config_info("test_env")
    assert info["name"] == "test_env"
    assert info["database"]["url"] == "sqlite+aiosqlite:///test.db"

    # Delete config
    assert manager.delete_config("test_env") is True
    assert "test_env" not in manager.get_available_configs()

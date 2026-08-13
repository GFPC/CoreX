"""
Unit tests for GFP CoreX AuthService, JWT creation, and password hashing.
"""

import pytest
from datetime import timedelta
from fastapi import HTTPException

from src.gfpcorex.services.auth import AuthService
from src.gfpcorex.core.config import Config, DatabaseConfig, AuthConfig, RedisConfig, AppConfig, LoggingConfig, SecurityConfig


@pytest.fixture
def mock_config():
    return Config(
        db=DatabaseConfig(url="sqlite+aiosqlite:///:memory:"),
        redis=RedisConfig(url="redis://localhost:6379/0"),
        auth=AuthConfig(secret_key="secretkey_" + "a" * 24, algorithm="HS256", access_token_expire_minutes=15),
        app=AppConfig(title="Test", version="1.0.0", debug=True),
        logging=LoggingConfig(),
        security=SecurityConfig()
    )


def test_password_hashing_and_verification(mock_config):
    auth_service = AuthService(mock_config)
    password = "MySecurePassword123!"

    hashed = auth_service.get_password_hash(password)
    assert hashed != password
    assert auth_service.verify_password(password, hashed) is True
    assert auth_service.verify_password("WrongPassword", hashed) is False


def test_jwt_access_token(mock_config):
    auth_service = AuthService(mock_config)
    token_payload = {"sub": "john_doe", "user_id": 1, "config_name": "dev"}

    token = auth_service.create_access_token(token_payload)
    assert isinstance(token, str)

    decoded = auth_service.verify_token(token)
    assert decoded.username == "john_doe"
    assert decoded.user_id == 1
    assert decoded.config_name == "dev"


def test_jwt_perpetual_token(mock_config):
    auth_service = AuthService(mock_config)
    token_payload = {"sub": "system_bot", "user_id": 99, "config_name": "prod"}

    token = auth_service.create_perpetual_token(token_payload)
    decoded = auth_service.verify_token(token)
    assert decoded.username == "system_bot"
    assert decoded.user_id == 99


def test_invalid_jwt_token(mock_config):
    auth_service = AuthService(mock_config)
    with pytest.raises(HTTPException) as exc_info:
        auth_service.verify_token("invalid.token.signature")
    assert exc_info.value.status_code == 401

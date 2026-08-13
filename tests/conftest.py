"""
Shared pytest fixtures for GFP CoreX test suite.
Provides reusable Config instances and mock data for all tests.
"""

import pytest

from src.gfpcorex.core.config import (
    AppConfig,
    AuthConfig,
    Config,
    DatabaseConfig,
    LoggingConfig,
    RedisConfig,
    SecurityConfig,
)


@pytest.fixture(scope="session")
def base_config() -> Config:
    """Shared base Config object reused across the entire test session."""
    return Config(
        db=DatabaseConfig(url="sqlite+aiosqlite:///:memory:"),
        redis=RedisConfig(url="redis://localhost:6379/0"),
        auth=AuthConfig(
            secret_key="test_secret_key_must_be_32_chars!",
            algorithm="HS256",
            access_token_expire_minutes=15,
        ),
        app=AppConfig(
            title="CoreX Test",
            version="0.0.1",
            debug=True,
            cors_origins=["*"],
        ),
        logging=LoggingConfig(level="DEBUG", format="text", handlers=["console"]),
        security=SecurityConfig(bcrypt_rounds=4),  # Faster hashing for tests
    )


@pytest.fixture
def test_user_data() -> dict:
    """Sample user registration data."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
    }


@pytest.fixture
def safe_plugin_code() -> str:
    """A plugin code snippet that should pass security inspection."""
    return """
def add(a, b):
    return {"result": a + b}

def multiply(a, b):
    return {"result": a * b}

def greet(name: str) -> dict:
    return {"message": f"Hello, {name}!"}
"""


@pytest.fixture
def malicious_os_code() -> str:
    """Malicious plugin attempting to import os."""
    return "import os\ndef pwn():\n    os.system('rm -rf /')"


@pytest.fixture
def malicious_eval_code() -> str:
    """Malicious plugin using eval."""
    return "def run(expr):\n    return eval(expr)"

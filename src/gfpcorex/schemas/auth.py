"""
Authentication schemas for GFP CoreX API.
Fully migrated to Pydantic v2 field_validator syntax.
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


class UserBase(BaseModel):
    """Base user schema."""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="User email")
    first_name: Optional[str] = Field(None, max_length=50, description="First name")
    last_name: Optional[str] = Field(None, max_length=50, description="Last name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    bio: Optional[str] = Field(None, max_length=500, description="User bio")


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, max_length=128, description="Password")
    confirm_password: str = Field(..., description="Password confirmation")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username must contain only letters, numbers, and underscores')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v

    @model_validator(mode='after')
    def passwords_match(self) -> 'UserCreate':
        """Validate that password and confirm_password match."""
        if self.password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")
    expires_in: Optional[int] = Field(
        None, ge=0,
        description="Token expiration time in seconds. If not provided, token will be perpetual"
    )


class UserUpdate(BaseModel):
    """Schema for user profile update."""
    first_name: Optional[str] = Field(None, max_length=50, description="First name")
    last_name: Optional[str] = Field(None, max_length=50, description="Last name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    avatar_url: Optional[str] = Field(None, max_length=255, description="Avatar URL")
    bio: Optional[str] = Field(None, max_length=500, description="User bio")


class UserResponse(UserBase):
    """Schema for user response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    is_superuser: bool
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class UserProfile(UserResponse):
    """Schema for user profile (includes sensitive data)."""
    pass


class Token(BaseModel):
    """Schema for authentication token."""
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = Field(
        None, description="Token expiration time in seconds. None means perpetual token"
    )
    refresh_token: Optional[str] = None


class TokenData(BaseModel):
    """Schema for token payload data."""
    username: Optional[str] = None
    user_id: Optional[int] = None
    config_name: Optional[str] = None


def _validate_password_strength(v: str) -> str:
    """Shared password strength validator."""
    if not re.search(r'[A-Z]', v):
        raise ValueError('Password must contain at least one uppercase letter')
    if not re.search(r'[a-z]', v):
        raise ValueError('Password must contain at least one lowercase letter')
    if not re.search(r'\d', v):
        raise ValueError('Password must contain at least one digit')
    return v


class PasswordChange(BaseModel):
    """Schema for password change."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(..., description="Password confirmation")

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password strength."""
        return _validate_password_strength(v)

    @model_validator(mode='after')
    def passwords_match(self) -> 'PasswordChange':
        if self.new_password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self

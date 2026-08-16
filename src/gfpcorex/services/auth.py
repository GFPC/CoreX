"""
Authentication service for GFP CoreX.
Supports multi-configuration user management.
"""

from datetime import UTC, datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import Config
from ..models.auth_session import AuthSession
from ..models.user import User
from ..schemas.auth import PasswordChange, TokenData, UserCreate

# bcrypt rejects inputs longer than 72 bytes; truncate consistently before hashing.
_BCRYPT_MAX_BYTES = 72


class AuthService:
    """Authentication service for user management."""
    
    def __init__(self, config: Config):
        self.config = config
        self.secret_key = config.auth.secret_key
        self.algorithm = config.auth.algorithm
        self.access_token_expire_minutes = config.auth.access_token_expire_minutes
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its bcrypt hash."""
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES],
                hashed_password.encode("utf-8"),
            )
        except (ValueError, TypeError):
            return False

    def get_password_hash(self, password: str) -> str:
        """Hash a password with bcrypt using the configured cost factor."""
        salt = bcrypt.gensalt(rounds=self.config.security.bcrypt_rounds)
        hashed = bcrypt.hashpw(password.encode("utf-8")[:_BCRYPT_MAX_BYTES], salt)
        return hashed.decode("utf-8")
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_perpetual_token(self, data: dict) -> str:
        """Create a perpetual JWT access token (no expiration)."""
        to_encode = data.copy()
        # No expiration date for perpetual tokens
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> TokenData:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            user_id: int = payload.get("user_id")
            config_name: str = payload.get("config_name")
            
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return TokenData(username=username, user_id=user_id, config_name=config_name)
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def authenticate_user(self, session: AsyncSession, username: str, password: str) -> Optional[User]:
        """Authenticate a user with username/email and password."""
        # Try to find user by username or email
        stmt = select(User).where(
            or_(
                User.username == username,
                User.email == username
            )
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        if not self.verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            return None
        
        return user
    
    async def get_user_by_id(self, session: AsyncSession, user_id: int) -> Optional[User]:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, session: AsyncSession, username: str) -> Optional[User]:
        """Get user by username."""
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, session: AsyncSession, email: str) -> Optional[User]:
        """Get user by email."""
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_user(self, session: AsyncSession, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if username already exists
        existing_user = await self.get_user_by_username(session, user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check if email already exists
        existing_email = await self.get_user_by_email(session, user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = self.get_password_hash(user_data.password)
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            bio=user_data.bio
        )
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        return user
    
    async def create_auth_session(self, session: AsyncSession, user_id: int, token: str, expires_in: Optional[int] = None) -> AuthSession:
        """Create a new authentication session."""
        expires_at = None
        if expires_in is not None:
            expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
        
        auth_session = AuthSession(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
        
        session.add(auth_session)
        await session.commit()
        await session.refresh(auth_session)
        
        return auth_session
    
    async def get_auth_session_by_token(self, session: AsyncSession, token: str) -> Optional[AuthSession]:
        """Get authentication session by token."""
        stmt = select(AuthSession).where(AuthSession.token == token)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_auth_session(self, session: AsyncSession, token: str) -> bool:
        """Delete an authentication session by its token (revoke it on logout)."""
        auth_session = await self.get_auth_session_by_token(session, token)
        if auth_session is None:
            return False
        await session.delete(auth_session)
        await session.commit()
        return True

    async def delete_expired_sessions(self, session: AsyncSession) -> int:
        """Delete expired sessions."""
        from sqlalchemy import and_
        
        stmt = select(AuthSession).where(
            and_(
                AuthSession.expires_at.isnot(None),
                AuthSession.expires_at < datetime.now(UTC)
            )
        )
        result = await session.execute(stmt)
        expired_sessions = result.scalars().all()
        
        for expired_session in expired_sessions:
            await session.delete(expired_session)
        
        await session.commit()
        return len(expired_sessions)
    
    async def update_user_profile(self, session: AsyncSession, user_id: int, user_data: dict) -> User:
        """Update user profile."""
        user = await self.get_user_by_id(session, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update fields
        for field, value in user_data.items():
            if value is not None and hasattr(user, field):
                setattr(user, field, value)
        
        await session.commit()
        await session.refresh(user)
        
        return user
    
    async def change_password(self, session: AsyncSession, user_id: int, password_data: PasswordChange) -> bool:
        """Change user password."""
        user = await self.get_user_by_id(session, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not self.verify_password(password_data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        user.hashed_password = self.get_password_hash(password_data.new_password)
        await session.commit()
        
        return True
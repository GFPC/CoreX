"""
Authentication API routes for GFP CoreX.

Tokens are supplied via the standard ``Authorization: Bearer <token>`` header
(resolved in ``api.deps``); no endpoint accepts a token in the request body.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select

from ..models.user import User
from ..schemas.auth import (
    PasswordChange,
    Token,
    UserCreate,
    UserLogin,
    UserProfile,
    UserResponse,
    UserUpdate,
)
from ..services.auth import AuthService
from .deps import (
    ConfigDep,
    CurrentActiveUser,
    CurrentSuperuser,
    DbDep,
    bearer_scheme,
)


def create_universal_auth_router() -> APIRouter:
    """Create the universal authentication router for all configurations."""

    router = APIRouter(prefix="/auth", tags=["Authentication"])

    @router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
    async def register(
        config: ConfigDep,
        session: DbDep,
        user_data: UserCreate,
        config_name: str,
    ):
        """Register a new user and return a finite access token.

        The account is created and a session-backed JWT is issued with the
        configuration's default lifetime (``access_token_expire_minutes``).
        """
        auth_service = AuthService(config)
        user = await auth_service.create_user(session, user_data)

        ttl_seconds = config.auth.access_token_expire_minutes * 60
        token_data = {
            "sub": user.username,
            "user_id": user.id,
            "config_name": config_name,
        }
        access_token = auth_service.create_access_token(
            data=token_data,
            expires_delta=timedelta(seconds=ttl_seconds),
        )
        await auth_service.create_auth_session(session, user.id, access_token, ttl_seconds)

        return Token(access_token=access_token, token_type="bearer", expires_in=ttl_seconds)

    @router.post("/login", response_model=Token)
    async def login(
        config: ConfigDep,
        session: DbDep,
        user_credentials: UserLogin,
        config_name: str,
    ):
        """Authenticate a user and return an access token.

        The token expires after the configured lifetime by default. Supply
        ``expires_in`` (seconds) to override it, or ``0`` to explicitly request
        a perpetual token.
        """
        auth_service = AuthService(config)
        user = await auth_service.authenticate_user(
            session,
            user_credentials.username,
            user_credentials.password,
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token_data = {
            "sub": user.username,
            "user_id": user.id,
            "config_name": config_name,
        }

        requested = user_credentials.expires_in
        if requested == 0:
            # Explicit opt-in to a non-expiring token.
            access_token = auth_service.create_perpetual_token(token_data)
            token_ttl = None
        else:
            # Default to the configured lifetime when no override is requested.
            token_ttl = (
                requested
                if requested is not None
                else config.auth.access_token_expire_minutes * 60
            )
            access_token = auth_service.create_access_token(
                data=token_data,
                expires_delta=timedelta(seconds=token_ttl),
            )

        await auth_service.create_auth_session(session, user.id, access_token, token_ttl)

        return Token(access_token=access_token, token_type="bearer", expires_in=token_ttl)

    @router.post("/logout")
    async def logout(
        config: ConfigDep,
        session: DbDep,
        current_user: CurrentActiveUser,
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    ):
        """Revoke the presented token by deleting its persisted session row."""
        auth_service = AuthService(config)
        await auth_service.delete_auth_session(session, credentials.credentials)
        return {"message": "Logged out successfully"}

    @router.get("/me", response_model=UserProfile)
    async def get_current_user_profile(current_user: CurrentActiveUser):
        """Return the authenticated user's profile."""
        return UserProfile.model_validate(current_user)

    @router.put("/me", response_model=UserProfile)
    async def update_current_user_profile(
        config: ConfigDep,
        session: DbDep,
        user_update: UserUpdate,
        current_user: CurrentActiveUser,
    ):
        """Update the authenticated user's profile."""
        auth_service = AuthService(config)
        update_data = user_update.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data provided for update",
            )

        updated_user = await auth_service.update_user_profile(
            session, current_user.id, update_data
        )
        return UserProfile.model_validate(updated_user)

    @router.post("/me/change-password")
    async def change_password(
        config: ConfigDep,
        session: DbDep,
        password_data: PasswordChange,
        current_user: CurrentActiveUser,
    ):
        """Change the authenticated user's password."""
        auth_service = AuthService(config)
        await auth_service.change_password(session, current_user.id, password_data)
        return {"message": "Password changed successfully"}

    @router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_current_user(
        session: DbDep,
        current_user: CurrentActiveUser,
    ):
        """Soft-delete the authenticated user's account (marks it inactive)."""
        current_user.is_active = False
        await session.commit()
        return None

    @router.get("/users/{user_id}", response_model=UserResponse)
    async def get_user_by_id(
        config: ConfigDep,
        session: DbDep,
        user_id: int,
        current_user: CurrentActiveUser,
    ):
        """Return a user by ID (any authenticated user)."""
        auth_service = AuthService(config)
        user = await auth_service.get_user_by_id(session, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return UserResponse.model_validate(user)

    @router.get("/users/username/{username}", response_model=UserResponse)
    async def get_user_by_username(
        config: ConfigDep,
        session: DbDep,
        username: str,
        current_user: CurrentActiveUser,
    ):
        """Return a user by username (any authenticated user)."""
        auth_service = AuthService(config)
        user = await auth_service.get_user_by_username(session, username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return UserResponse.model_validate(user)

    # Admin endpoints (superuser only)
    @router.get("/admin/users", response_model=list[UserResponse])
    async def get_all_users(
        session: DbDep,
        current_user: CurrentSuperuser,
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    ):
        """Return all users in the configuration (superuser only)."""
        stmt = select(User).offset(skip).limit(limit)
        result = await session.execute(stmt)
        users = result.scalars().all()
        return [UserResponse.model_validate(user) for user in users]

    @router.post("/admin/users/{user_id}/activate")
    async def activate_user(
        config: ConfigDep,
        session: DbDep,
        user_id: int,
        current_user: CurrentSuperuser,
    ):
        """Activate a user account (superuser only)."""
        auth_service = AuthService(config)
        user = await auth_service.get_user_by_id(session, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        user.is_active = True
        await session.commit()
        return {"message": f"User {user.username} activated successfully"}

    @router.post("/admin/users/{user_id}/deactivate")
    async def deactivate_user(
        config: ConfigDep,
        session: DbDep,
        user_id: int,
        current_user: CurrentSuperuser,
    ):
        """Deactivate a user account (superuser only)."""
        auth_service = AuthService(config)
        user = await auth_service.get_user_by_id(session, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        user.is_active = False
        await session.commit()
        return {"message": f"User {user.username} deactivated successfully"}

    return router

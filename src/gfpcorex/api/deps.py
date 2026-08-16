"""
Shared FastAPI dependencies for GFP CoreX.

Centralizes per-configuration resolution, database-session lifecycle, and
header-based Bearer authentication so routers stop duplicating config lookups
and no longer accept the JWT in the request body.
"""

from typing import Annotated, AsyncIterator

from fastapi import Depends, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import Config, get_config
from ..core.database import db_manager
from ..models.user import User
from ..services.auth import AuthService

# Extracts and validates the "Authorization: Bearer <token>" header.
bearer_scheme = HTTPBearer()


def get_config_dep(config_name: str = Path(...)) -> Config:
    """Resolve the ``Config`` for the ``{config_name}`` path parameter.

    Raises 404 when the configuration is missing and 400 when it is invalid,
    replacing the identical try/except block that used to live in every route.
    """
    try:
        return get_config(config_name)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration '{config_name}' not found",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid configuration '{config_name}': {e}",
        )


ConfigDep = Annotated[Config, Depends(get_config_dep)]


async def get_db(
    config: ConfigDep,
    config_name: str = Path(...),
) -> AsyncIterator[AsyncSession]:
    """Yield a database session bound to the current configuration.

    Rolls back on error and always closes the session, so routes never manage
    the session lifecycle by hand. Commits are performed by the service layer.
    """
    session = db_manager.create_session(config_name, config)
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


DbDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    config: ConfigDep,
    session: DbDep,
    config_name: str = Path(...),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    """Authenticate the caller from the ``Authorization: Bearer`` header.

    Validates the JWT signature, binds the token to this configuration, checks
    the persisted session row for revocation/expiry, and loads the user.
    """
    auth_service = AuthService(config)
    token = credentials.credentials
    token_data = auth_service.verify_token(token)

    # A token minted for another configuration must not authenticate here.
    if token_data.config_name != config_name:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not valid for this configuration",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # The token must map to a live session row; logout or expiry revokes it.
    auth_session = await auth_service.get_auth_session_by_token(session, token)
    if auth_session is None or auth_session.is_expired:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked or has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await auth_service.get_user_by_id(session, token_data.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_active_user(current_user: CurrentUser) -> User:
    """Ensure the authenticated user's account is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user


CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]


async def get_current_superuser(current_user: CurrentActiveUser) -> User:
    """Ensure the authenticated user has superuser privileges."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


CurrentSuperuser = Annotated[User, Depends(get_current_superuser)]

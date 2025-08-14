"""
Authentication API routes for GFP CoreX.
Supports multi-configuration user management.
"""

from datetime import timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User
from ..models.auth_session import AuthSession
from ..schemas.auth import (
    UserCreate, UserLogin, UserResponse, UserProfile, 
    UserUpdate, Token, PasswordChange, TokenRequest,
    UserUpdateWithToken, PasswordChangeWithToken, UserProfileRequest,
    UserDeleteRequest, AdminUsersRequest, AdminUserActionRequest
)
from ..services.auth import (
    AuthService, get_current_active_user_from_token, 
    get_current_superuser_from_token, get_current_user_from_token
)
from ..core.config import get_config
from ..core.database import get_session_auto_cleanup, commit_and_close_session

def create_universal_auth_router() -> APIRouter:
    """Create universal authentication router for all configurations."""
    
    router = APIRouter(prefix="/auth", tags=["Authentication"])
    
    @router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
    async def register(
        config_name: str,
        user_data: UserCreate,
        request: Request
    ):
        """
        Register a new user and return perpetual token.
        
        This endpoint creates a new user account and automatically issues a perpetual token.
        
        **Features:**
        - Creates user account with profile information
        - Automatically generates perpetual token (no expiration)
        - Saves session to database for tracking
        - Returns token with user information
        
        **Response includes:**
        - `access_token`: JWT token for authentication
        - `token_type`: Always "bearer"
        - `expires_in`: None (perpetual token)
        - `user`: Complete user profile information
        """
        try:
            config = get_config(config_name)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{config_name}' not found"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid configuration '{config_name}': {str(e)}"
            )
        
        auth_service = AuthService(config)
        
        session = await get_session_auto_cleanup(config_name, config)
        try:
            # Create user
            user = await auth_service.create_user(session, user_data)
            
            # Create perpetual token
            token_data = {
                "sub": user.username,
                "user_id": user.id,
                "config_name": config_name
            }
            access_token = auth_service.create_perpetual_token(token_data)
            
            # Save session to database
            await auth_service.create_auth_session(session, user.id, access_token)
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": None,  # Perpetual token
                "user": UserResponse.from_orm(user)
            }
        except HTTPException:
            await session.close()
            raise
        except Exception as e:
            await session.close()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create user: {str(e)}"
            )
        finally:
            await commit_and_close_session(session)
    
    @router.post("/login", response_model=Token)
    async def login(
        config_name: str,
        user_credentials: UserLogin,
        request: Request
    ):
        """
        Login user and get access token.
        
        This endpoint authenticates a user and returns a JWT token.
        
        **Token Expiration:**
        - If `expires_in` is not provided: perpetual token (no expiration)
        - If `expires_in` is provided: token expires in specified seconds
        
        **Parameters:**
        - `username`: Username or email address
        - `password`: User password
        - `expires_in`: Optional expiration time in seconds (0 = perpetual)
        
        **Response includes:**
        - `access_token`: JWT token for authentication
        - `token_type`: Always "bearer"
        - `expires_in`: Expiration time in seconds or None (perpetual)
        - `user`: Complete user profile information
        """
        try:
            config = get_config(config_name)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{config_name}' not found"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid configuration '{config_name}': {str(e)}"
            )
        
        auth_service = AuthService(config)
        
        session = await get_session_auto_cleanup(config_name, config)
        try:
            user = await auth_service.authenticate_user(
                session, 
                user_credentials.username, 
                user_credentials.password
            )
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Determine token expiration
            expires_in = user_credentials.expires_in
            if expires_in is None:
                # Create perpetual token
                token_data = {
                    "sub": user.username,
                    "user_id": user.id,
                    "config_name": config_name
                }
                access_token = auth_service.create_perpetual_token(token_data)
                expires_in_seconds = None
            else:
                # Create token with specified expiration
                token_data = {
                    "sub": user.username,
                    "user_id": user.id,
                    "config_name": config_name
                }
                access_token = auth_service.create_access_token(
                    data=token_data,
                    expires_delta=timedelta(seconds=expires_in)
                )
                expires_in_seconds = expires_in
            
            # Save session to database
            await auth_service.create_auth_session(session, user.id, access_token, expires_in)
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": expires_in_seconds,
                "user": UserResponse.from_orm(user)
            }
        finally:
            await commit_and_close_session(session)
    
    @router.post("/me", response_model=UserProfile)
    async def get_current_user_profile(
        config_name: str,
        request_data: UserProfileRequest
    ):
        """
        Get current user profile.
        
        This endpoint returns the profile of the currently authenticated user.
        """
        try:
            current_user = await get_current_active_user_from_token(config_name, request_data.token)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{config_name}' not found"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid configuration '{config_name}': {str(e)}"
            )
        
        return UserProfile.from_orm(current_user)
    
    @router.put("/me", response_model=UserProfile)
    async def update_current_user_profile(
        config_name: str,
        request_data: UserUpdateWithToken
    ):
        """
        Update current user profile.
        
        This endpoint allows users to update their profile information.
        """
        try:
            config = get_config(config_name)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{config_name}' not found"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid configuration '{config_name}': {str(e)}"
            )
        
        auth_service = AuthService(config)
        current_user = await get_current_active_user_from_token(config_name, request_data.token)
        
        session = await get_session_auto_cleanup(config_name, config)
        try:
            # Convert Pydantic model to dict, excluding token and None values
            update_data = request_data.dict(exclude={'token'}, exclude_unset=True)
            
            if not update_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No data provided for update"
                )
            
            updated_user = await auth_service.update_user_profile(
                session, current_user.id, update_data
            )
            
            return UserProfile.from_orm(updated_user)
        finally:
            await commit_and_close_session(session)
    
    @router.post("/change-password")
    async def change_password(
        config_name: str,
        request_data: PasswordChangeWithToken
    ):
        """
        Change user password.
        
        This endpoint allows users to change their password.
        """
        try:
            config = get_config(config_name)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{config_name}' not found"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid configuration '{config_name}': {str(e)}"
            )
        
        auth_service = AuthService(config)
        current_user = await get_current_active_user_from_token(config_name, request_data.token)
        
        session = await get_session_auto_cleanup(config_name, config)
        try:
            # Create PasswordChange object from request data
            password_data = PasswordChange(
                current_password=request_data.current_password,
                new_password=request_data.new_password,
                confirm_password=request_data.confirm_password
            )
            
            success = await auth_service.change_password(
                session, current_user.id, password_data
            )
            
            if success:
                return {"message": "Password changed successfully"}
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to change password"
                )
        finally:
            await commit_and_close_session(session)
    
    @router.post("/users/{user_id}", response_model=UserResponse)
    async def get_user_by_id(
        config_name: str,
        user_id: int,
        request_data: TokenRequest
    ):
        """
        Get user by ID.
        
        This endpoint returns user information by ID (accessible to authenticated users).
        """
        try:
            config = get_config(config_name)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{config_name}' not found"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid configuration '{config_name}': {str(e)}"
            )
        
        auth_service = AuthService(config)
        current_user = await get_current_active_user_from_token(config_name, request_data.token)
        
        session = await get_session_auto_cleanup(config_name, config)
        try:
            user = await auth_service.get_user_by_id(session, user_id)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            return UserResponse.from_orm(user)
        finally:
            await commit_and_close_session(session)
    
    @router.post("/users/username/{username}", response_model=UserResponse)
    async def get_user_by_username(
        config_name: str,
        username: str,
        request_data: TokenRequest
    ):
        """
        Get user by username.
        
        This endpoint returns user information by username (accessible to authenticated users).
        """
        try:
            config = get_config(config_name)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{config_name}' not found"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid configuration '{config_name}': {str(e)}"
            )
        
        auth_service = AuthService(config)
        current_user = await get_current_active_user_from_token(config_name, request_data.token)
        
        session = await get_session_auto_cleanup(config_name, config)
        try:
            user = await auth_service.get_user_by_username(session, user_id)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            return UserResponse.from_orm(user)
        finally:
            await commit_and_close_session(session)
    
    @router.post("/me/delete", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_current_user(
        config_name: str,
        request_data: UserDeleteRequest
    ):
        """
        Delete current user account.
        
        This endpoint allows users to delete their own account.
        """
        try:
            config = get_config(config_name)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{config_name}' not found"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid configuration '{config_name}': {str(e)}"
            )
        
        current_user = await get_current_active_user_from_token(config_name, request_data.token)
        
        session = await get_session_auto_cleanup(config_name, config)
        try:
            # Soft delete - mark as inactive
            current_user.is_active = False
            await session.commit()
            
            return None
        finally:
            await commit_and_close_session(session)
    
    # Admin endpoints (superuser only)
    @router.post("/admin/users", response_model=list[UserResponse])
    async def get_all_users(
        config_name: str,
        request_data: AdminUsersRequest
    ):
        """
        Get all users (admin only).
        
        This endpoint returns all users in the configuration (superuser only).
        """
        try:
            config = get_config(config_name)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{config_name}' not found"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid configuration '{config_name}': {str(e)}"
            )
        
        current_user = await get_current_superuser_from_token(config_name, request_data.token)
        
        session = await get_session_auto_cleanup(config_name, config)
        try:
            from sqlalchemy import select
            stmt = select(User).offset(request_data.skip).limit(request_data.limit)
            result = await session.execute(stmt)
            users = result.scalars().all()
            
            return [UserResponse.from_orm(user) for user in users]
        finally:
            await commit_and_close_session(session)
    
    @router.post("/admin/users/activate")
    async def activate_user(
        config_name: str,
        request_data: AdminUserActionRequest
    ):
        """
        Activate user account (admin only).
        
        This endpoint allows superusers to activate user accounts.
        """
        try:
            config = get_config(config_name)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{config_name}' not found"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid configuration '{config_name}': {str(e)}"
            )
        
        auth_service = AuthService(config)
        current_user = await get_current_superuser_from_token(config_name, request_data.token)
        
        session = await get_session_auto_cleanup(config_name, config)
        try:
            user = await auth_service.get_user_by_id(session, request_data.user_id)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            user.is_active = True
            await session.commit()
            
            return {"message": f"User {user.username} activated successfully"}
        finally:
            await commit_and_close_session(session)
    
    @router.post("/admin/users/deactivate")
    async def deactivate_user(
        config_name: str,
        request_data: AdminUserActionRequest
    ):
        """
        Deactivate user account (admin only).
        
        This endpoint allows superusers to deactivate user accounts.
        """
        try:
            config = get_config(config_name)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{config_name}' not found"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid configuration '{config_name}': {str(e)}"
            )
        
        auth_service = AuthService(config)
        current_user = await get_current_superuser_from_token(config_name, request_data.token)
        
        session = await get_session_auto_cleanup(config_name, config)
        try:
            user = await auth_service.get_user_by_id(session, request_data.user_id)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            user.is_active = False
            await session.commit()
            
            return {"message": f"User {user.username} deactivated successfully"}
        finally:
            await commit_and_close_session(session)
    
    return router

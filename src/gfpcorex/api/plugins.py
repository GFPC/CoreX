"""
Plugin management API routes for GFP CoreX.
Supports creating, loading and executing user-created plugins.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..plugins.manager import plugin_manager
from ..plugins.api import get_plugin_api
from ..core.database import get_session_auto_cleanup, commit_and_close_session
from ..core.config import get_config
from ..models.plugin import Plugin
from sqlalchemy import select


class PluginCreate(BaseModel):
    name: str
    code: str


class PluginUpdate(BaseModel):
    code: str
    is_active: bool = True


class PluginInfo(BaseModel):
    id: int
    name: str
    is_active: bool
    functions: List[str]
    created_at: str
    updated_at: str


class PluginExecute(BaseModel):
    function_name: str
    args: List[Any] = []
    kwargs: Dict[str, Any] = {}


def create_plugin_router() -> APIRouter:
    """Create plugin management router."""
    
    router = APIRouter(prefix="/plugins", tags=["Plugin Management"])
    
    @router.get("/", response_model=List[PluginInfo])
    async def list_plugins(config_name: str):
        """
        List all loaded plugins.
        
        Returns information about all loaded plugins.
        """
        try:
            plugins = []
            for plugin_name in plugin_manager.get_loaded_plugins(config_name):
                info = plugin_manager.get_plugin_info(plugin_name, config_name)
                if info:
                    # Convert datetime to string
                    info["created_at"] = info["created_at"].isoformat()
                    info["updated_at"] = info["updated_at"].isoformat()
                    plugins.append(PluginInfo(**info))
            
            return plugins
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list plugins: {str(e)}"
            )
    
    @router.get("/{plugin_name}", response_model=PluginInfo)
    async def get_plugin_info(plugin_name: str, config_name: str):
        """
        Get plugin information.
        
        Returns detailed information about a specific plugin.
        """
        try:
            info = plugin_manager.get_plugin_info(plugin_name, config_name)
            if info:
                # Convert datetime to string
                info["created_at"] = info["created_at"].isoformat()
                info["updated_at"] = info["updated_at"].isoformat()
                return PluginInfo(**info)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Plugin '{plugin_name}' not found in config '{config_name}'"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get plugin info: {str(e)}"
            )
    
    @router.post("/", response_model=Dict[str, Any])
    async def create_plugin(plugin_data: PluginCreate, config_name: str):
        """
        Create a new plugin.
        
        Creates a new plugin with the specified code.
        """
        try:
            config = get_config(config_name)
            
            # Calculate hash
            import hashlib
            hashsum = hashlib.sha256(plugin_data.code.encode()).hexdigest()
            
            session = await get_session_auto_cleanup(config_name, config)
            try:
                # Check if plugin with this name already exists
                result = await session.execute(
                    select(Plugin).where(Plugin.name == plugin_data.name)
                )
                existing_plugin = result.scalar_one_or_none()
                
                if existing_plugin:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Plugin with name '{plugin_data.name}' already exists"
                    )
                
                # Create new plugin
                plugin = Plugin(
                    name=plugin_data.name,
                    code=plugin_data.code,
                    hashsum=hashsum,
                    is_active=True
                )
                
                session.add(plugin)
                await session.commit()
                await session.refresh(plugin)
                
                # Load the plugin
                success = await plugin_manager.load_plugin(plugin, config_name)
                
                return {
                    "message": f"Plugin '{plugin_data.name}' created successfully",
                    "plugin_id": plugin.id,
                    "loaded": success
                }
            finally:
                await commit_and_close_session(session)
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create plugin: {str(e)}"
            )
    
    @router.put("/{plugin_name}", response_model=Dict[str, Any])
    async def update_plugin(plugin_name: str, plugin_data: PluginUpdate, config_name: str):
        """
        Update an existing plugin.
        
        Updates plugin code and settings.
        """
        try:
            config = get_config(config_name)
            
            # Calculate hash
            import hashlib
            hashsum = hashlib.sha256(plugin_data.code.encode()).hexdigest()
            
            session = await get_session_auto_cleanup(config_name, config)
            try:
                # Get existing plugin
                result = await session.execute(
                    select(Plugin).where(Plugin.name == plugin_name)
                )
                plugin = result.scalar_one_or_none()
                
                if not plugin:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Plugin '{plugin_name}' not found"
                    )
                
                # Update plugin
                plugin.code = plugin_data.code
                plugin.hashsum = hashsum
                plugin.is_active = plugin_data.is_active
                
                await session.commit()
                
                # Reload the plugin
                success = await plugin_manager.reload_plugin(plugin_name, config_name)
                
                return {
                    "message": f"Plugin '{plugin_name}' updated successfully",
                    "reloaded": success
                }
            finally:
                await commit_and_close_session(session)
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update plugin: {str(e)}"
            )
    
    @router.post("/{plugin_name}/execute", response_model=Dict[str, Any])
    async def execute_plugin_function(plugin_name: str, execute_data: PluginExecute, config_name: str):
        """
        Execute a plugin function.
        
        Executes a specific function from a plugin.
        """
        try:
            # Check if plugin is loaded
            if plugin_name not in plugin_manager.get_loaded_plugins(config_name):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Plugin '{plugin_name}' is not loaded in config '{config_name}'"
                )
            
            # Execute function
            result = await plugin_manager.call_plugin_function(
                plugin_name,
                execute_data.function_name,
                config_name,
                *execute_data.args,
                **execute_data.kwargs
            )
            
            return {
                "plugin_name": plugin_name,
                "function_name": execute_data.function_name,
                "result": result,
                "success": result is not None
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to execute plugin function: {str(e)}"
            )
    
    @router.post("/{plugin_name}/reload", response_model=Dict[str, Any])
    async def reload_plugin(plugin_name: str, config_name: str):
        """
        Reload a plugin.
        
        Reloads a specific plugin from database.
        """
        try:
            success = await plugin_manager.reload_plugin(plugin_name, config_name)
            
            if success:
                return {
                    "message": f"Plugin '{plugin_name}' reloaded successfully"
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to reload plugin '{plugin_name}'"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to reload plugin: {str(e)}"
            )
    
    @router.delete("/{plugin_name}")
    async def delete_plugin(plugin_name: str, config_name: str):
        """
        Delete a plugin.
        
        Removes a plugin from the system.
        """
        try:
            config = get_config(config_name)
            
            session = await get_session_auto_cleanup(config_name, config)
            try:
                # Get plugin
                result = await session.execute(
                    select(Plugin).where(Plugin.name == plugin_name)
                )
                plugin = result.scalar_one_or_none()
                
                if not plugin:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Plugin '{plugin_name}' not found"
                    )
                
                # Remove from loaded plugins
                if plugin_name in plugin_manager.get_loaded_plugins():
                    # This would need to be implemented in plugin_manager
                    pass
                
                # Delete from database
                await session.delete(plugin)
                await session.commit()
                
                return {
                    "message": f"Plugin '{plugin_name}' deleted successfully"
                }
            finally:
                await commit_and_close_session(session)
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete plugin: {str(e)}"
            )
    
    return router 
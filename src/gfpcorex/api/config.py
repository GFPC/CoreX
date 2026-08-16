"""
Configuration management API routes for GFP CoreX.
Supports dynamic configuration creation and management.
"""

from fastapi import APIRouter, HTTPException, status

from ..core.config import (
    clear_config_cache,
    create_config,
    delete_config,
    get_available_configs,
    get_config_info,
    reload_config,
    update_config,
)
from ..core.database import db_manager
from ..schemas.config import (
    ConfigCreate,
    ConfigInfo,
    ConfigList,
    ConfigResponse,
    ConfigUpdate,
)


def create_config_router() -> APIRouter:
    """Create configuration management router."""
    
    router = APIRouter(prefix="/configs", tags=["Configuration Management"])
    
    @router.get("/", response_model=ConfigList)
    async def list_configurations():
        """
        List all available configurations.
        
        Returns information about all configurations without loading full configs.
        """
        try:
            config_names = get_available_configs()
            configs = []
            
            for config_name in config_names:
                config_info = get_config_info(config_name)
                configs.append(ConfigInfo(**config_info))
            
            return ConfigList(configs=configs, total=len(configs))
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list configurations: {str(e)}"
            )
    
    @router.get("/{config_name}", response_model=ConfigInfo)
    async def get_configuration_info(config_name: str):
        """
        Get configuration information.
        
        Returns detailed information about a specific configuration.
        """
        try:
            config_info = get_config_info(config_name)
            return ConfigInfo(**config_info)
            
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{config_name}' not found"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get configuration info: {str(e)}"
            )
    
    @router.post("/", response_model=ConfigResponse, status_code=status.HTTP_201_CREATED)
    async def create_configuration(config_data: ConfigCreate):
        """
        Create a new configuration.
        
        Creates a new configuration with the specified settings.
        The configuration will be immediately available for use.
        """
        try:
            # Convert Pydantic model to dict
            config_dict = config_data.model_dump()
            
            # Generate config name from database name
            db_name = config_data.db.url.split("/")[-1].split("?")[0]
            config_name = f"{db_name}_config"
            
            # Create the configuration
            config = create_config(config_name, config_dict)
            
            # Initialize database schema for the new configuration
            try:
                # Check if tables exist and create them if needed
                tables_exist = await db_manager.check_tables_exist(config_name, config)
                if not tables_exist:
                    success = await db_manager.create_tables_from_models(config_name, config)
                    if not success:
                        raise Exception("Failed to create tables from models")
            except Exception as e:
                # If schema initialization fails, delete the config
                try:
                    delete_config(config_name)
                except Exception:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to initialize database schema: {str(e)}"
                )
            
            return ConfigResponse(
                name=config_name,
                config=config_data,
                created=True
            )
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create configuration: {str(e)}"
            )
    
    @router.post("/{config_name}", response_model=ConfigResponse)
    async def create_configuration_with_name(config_name: str, config_data: ConfigCreate):
        """
        Create a new configuration with specific name.
        
        Creates a new configuration with the specified name and settings.
        """
        try:
            # Convert Pydantic model to dict
            config_dict = config_data.model_dump()
            
            # Create the configuration
            config = create_config(config_name, config_dict)
            
            # Initialize database schema for the new configuration
            try:
                # Check if tables exist and create them if needed
                tables_exist = await db_manager.check_tables_exist(config_name, config)
                if not tables_exist:
                    success = await db_manager.create_tables_from_models(config_name, config)
                    if not success:
                        raise Exception("Failed to create tables from models")
            except Exception as e:
                # If schema initialization fails, delete the config
                try:
                    delete_config(config_name)
                except Exception:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to initialize database schema: {str(e)}"
                )
            
            return ConfigResponse(
                name=config_name,
                config=config_data,
                created=True
            )
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create configuration: {str(e)}"
            )
    
    @router.put("/{config_name}", response_model=ConfigResponse)
    async def update_configuration(config_name: str, config_data: ConfigUpdate):
        """
        Update an existing configuration.
        
        Updates an existing configuration with new settings.
        Only provided fields will be updated.
        """
        try:
            # Get current config
            from ..core.config import get_config
            current_config = get_config(config_name)
            
            # Convert current config to dict
            current_dict = {
                "db": current_config.db.model_dump(),
                "redis": current_config.redis.model_dump(),
                "auth": current_config.auth.model_dump(),
                "app": current_config.app.model_dump(),
                "logging": current_config.logging.model_dump(),
                "security": current_config.security.model_dump()
            }

            # Update with new data (only provided fields)
            update_dict = config_data.model_dump(exclude_unset=True)
            for key, value in update_dict.items():
                if value is not None:
                    current_dict[key] = value.model_dump() if hasattr(value, 'model_dump') else value
            
            # Update the configuration
            update_config(config_name, current_dict)

            return ConfigResponse(
                name=config_name,
                config=ConfigCreate(**current_dict),
                created=False
            )
            
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{config_name}' not found"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update configuration: {str(e)}"
            )
    
    @router.delete("/{config_name}")
    async def delete_configuration(config_name: str):
        """
        Delete a configuration.
        
        Removes a configuration from the system.
        """
        try:
            success = delete_config(config_name)
            if success:
                return {"message": f"Configuration '{config_name}' deleted successfully"}
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete configuration"
                )
                
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{config_name}' not found"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete configuration: {str(e)}"
            )
    
    @router.post("/{config_name}/reload")
    async def reload_configuration(config_name: str):
        """
        Reload a configuration from file.
        
        Forces reload of configuration from the YAML file.
        """
        try:
            config = reload_config(config_name)
            return {
                "message": f"Configuration '{config_name}' reloaded successfully",
                "database": config.db.get_database_name()
            }
            
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{config_name}' not found"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to reload configuration: {str(e)}"
            )
    
    @router.post("/cache/clear")
    async def clear_cache():
        """
        Clear configuration cache.
        
        Clears the in-memory configuration cache.
        """
        try:
            clear_config_cache()
            return {"message": "Configuration cache cleared successfully"}
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to clear cache: {str(e)}"
            )
    
    return router 
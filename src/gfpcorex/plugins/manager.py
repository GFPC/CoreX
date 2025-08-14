"""
Plugin manager for GFP CoreX.
Handles loading, execution and management of user-created plugins.
"""

import asyncio
import hashlib
import importlib.util
import sys
import traceback
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.plugin import Plugin
from ..core.database import get_session_auto_cleanup, commit_and_close_session
from ..core.config import get_config
from ..utils.logging import GFPConsoleMessageStylizer

ConsoleMessageStylizer = GFPConsoleMessageStylizer("plugin_manager", "#ffa019")

class PluginManager:
    """Manages loading and execution of user-created plugins."""
    
    def __init__(self):
        # Изолированные плагины по конфигурациям
        self._loaded_plugins: Dict[str, Dict[str, Any]] = {}  # config_name -> {plugin_name -> plugin}
        self._plugin_modules: Dict[str, Dict[str, Any]] = {}  # config_name -> {plugin_name -> module}
        self._plugin_functions: Dict[str, Dict[str, Dict[str, Callable]]] = {}  # config_name -> {plugin_name -> {function_name -> function}}
    
    async def load_plugin(self, plugin: Plugin, config_name: str) -> bool:
        """
        Load a plugin from database into memory.
        
        Args:
            plugin: Plugin model instance
            config_name: Configuration name
            
        Returns:
            bool: True if plugin loaded successfully
        """
        try:
            # Check if plugin code has changed
            if plugin.is_code_changed():
                # Update hash
                plugin.hashsum = plugin.code_hash
            
            # Create unique module name
            module_name = f"plugin_{config_name}_{plugin.id}_{plugin.name}"
            
            # Create module spec
            spec = importlib.util.spec_from_loader(
                module_name, 
                loader=None
            )
            
            # Create module
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            
            # Execute plugin code
            exec(plugin.code, module.__dict__)
            
            # Initialize config-specific storage if needed
            if config_name not in self._loaded_plugins:
                self._loaded_plugins[config_name] = {}
                self._plugin_modules[config_name] = {}
                self._plugin_functions[config_name] = {}
            
            # Store loaded plugin
            self._loaded_plugins[config_name][plugin.name] = plugin
            self._plugin_modules[config_name][plugin.name] = module
            self._plugin_functions[config_name][plugin.name] = {}
            
            # Extract plugin functions
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if callable(attr) and not attr_name.startswith('_'):
                    self._plugin_functions[config_name][plugin.name][attr_name] = attr

            return True
            
        except Exception as e:
            ConsoleMessageStylizer.log(f"❌ Failed to load plugin '{plugin.name}' for config '{config_name}': {e}")
            traceback.print_exc()
            return False
    
    async def load_all_plugins(self, config_name: str) -> None:
        """
        Load all active plugins from database.
        
        Args:
            config_name: Configuration name
        """
        try:
            config = get_config(config_name)
            
            session = await get_session_auto_cleanup(config_name, config)
            try:
                # Get all active plugins
                result = await session.execute(
                    select(Plugin).where(Plugin.is_active == True)
                )
                plugins = result.scalars().all()

                for plugin in plugins:
                    await self.load_plugin(plugin, config_name)
            finally:
                await commit_and_close_session(session)
        except Exception as e:
            ConsoleMessageStylizer.log(f"❌ Error loading plugins: {e}")
    async def reload_plugin(self, plugin_name: str, config_name: str) -> bool:
        """
        Reload a specific plugin.
        
        Args:
            plugin_name: Name of plugin to reload
            config_name: Configuration name
            
        Returns:
            bool: True if plugin reloaded successfully
        """
        try:
            config = get_config(config_name)
            
            session = await get_session_auto_cleanup(config_name, config)
            try:
                # Get plugin from database
                result = await session.execute(
                    select(Plugin).where(Plugin.name == plugin_name)
                )
                plugin = result.scalar_one_or_none()
                
                if not plugin:
                    ConsoleMessageStylizer.log(f"❌ Plugin '{plugin_name}' not found")
                    return False
                
                # Remove old plugin
                if config_name in self._loaded_plugins and plugin_name in self._loaded_plugins[config_name]:
                    del self._loaded_plugins[config_name][plugin_name]
                    del self._plugin_modules[config_name][plugin_name]
                    del self._plugin_functions[config_name][plugin_name]
                
                # Load plugin again
                return await self.load_plugin(plugin, config_name)
            finally:
                await commit_and_close_session(session)
                
        except Exception as e:
            ConsoleMessageStylizer.log(f"❌ Error reloading plugin '{plugin_name}': {e}")
            return False
    
    def get_plugin_function(self, plugin_name: str, function_name: str, config_name: str) -> Optional[Callable]:
        """
        Get a function from a loaded plugin.
        
        Args:
            plugin_name: Name of the plugin
            function_name: Name of the function
            config_name: Configuration name
            
        Returns:
            Callable or None: Plugin function if found
        """
        if config_name in self._plugin_functions and plugin_name in self._plugin_functions[config_name]:
            return self._plugin_functions[config_name][plugin_name].get(function_name)
        return None
    
    async def call_plugin_function(self, plugin_name: str, function_name: str, config_name: str, *args, **kwargs) -> Any:
        """
        Call a function from a loaded plugin.
        
        Args:
            plugin_name: Name of the plugin
            function_name: Name of the function
            config_name: Configuration name
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Any: Function result
        """
        func = self.get_plugin_function(plugin_name, function_name, config_name)
        if func:
            try:
                # Check if function is async
                import asyncio
                import inspect
                
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                ConsoleMessageStylizer.log(f"❌ Error calling {plugin_name}.{function_name} for config '{config_name}': {e}")
                return None
        else:
            ConsoleMessageStylizer.log(f"❌ Function '{function_name}' not found in plugin '{plugin_name}' for config '{config_name}'")
            return None
    
    def get_loaded_plugins(self, config_name: str) -> List[str]:
        """Get list of loaded plugin names for a specific configuration."""
        if config_name in self._loaded_plugins:
            return list(self._loaded_plugins[config_name].keys())
        return []
    
    def get_plugin_info(self, plugin_name: str, config_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a loaded plugin.
        
        Args:
            plugin_name: Name of the plugin
            config_name: Configuration name
            
        Returns:
            Dict or None: Plugin information
        """
        if config_name in self._loaded_plugins and plugin_name in self._loaded_plugins[config_name]:
            plugin = self._loaded_plugins[config_name][plugin_name]
            functions = list(self._plugin_functions[config_name][plugin_name].keys())
            
            return {
                "name": plugin.name,
                "id": plugin.id,
                "is_active": plugin.is_active,
                "functions": functions,
                "created_at": plugin.created_at,
                "updated_at": plugin.updated_at
            }
        return None


# Global plugin manager instance
plugin_manager = PluginManager()




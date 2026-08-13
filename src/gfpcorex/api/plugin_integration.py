"""
API интеграция плагинов в другие эндпоинты
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..plugins.manager import plugin_manager

router = APIRouter(tags=["Plugin Integration"])

class PluginCallRequest(BaseModel):
    plugin_name: str
    function_name: str
    params: Dict[str, Any] = {}

class PluginCallResponse(BaseModel):
    success: bool
    result: Any
    error: Optional[str] = None

@router.post("/calculate", response_model=PluginCallResponse)
async def calculate_with_plugin(
    request: PluginCallRequest,
    config_name: str
):
    """
    Вызывает плагин для математических вычислений
    """
    try:
        # Получаем функцию из плагина
        plugin_func = plugin_manager.get_plugin_function(
            request.plugin_name, 
            request.function_name,
            config_name
        )
        
        if not plugin_func:
            raise HTTPException(
                status_code=404, 
                detail=f"Функция {request.function_name} не найдена в плагине {request.plugin_name} для конфигурации {config_name}"
            )
        
        # Вызываем функцию плагина
        result = await plugin_manager.call_plugin_function(
            request.plugin_name,
            request.function_name,
            config_name,
            **request.params
        )
        
        return PluginCallResponse(
            success=True,
            result=result
        )
        
    except Exception as e:
        return PluginCallResponse(
            success=False,
            result=None,
            error=str(e)
        )

@router.post("/greet", response_model=PluginCallResponse)
async def greet_with_plugin(
    request: PluginCallRequest,
    config_name: str
):
    """
    Вызывает плагин для приветствия
    """
    try:
        # Получаем функцию из плагина
        plugin_func = plugin_manager.get_plugin_function(
            request.plugin_name, 
            request.function_name,
            config_name
        )
        
        if not plugin_func:
            raise HTTPException(
                status_code=404, 
                detail=f"Функция {request.function_name} не найдена в плагине {request.plugin_name} для конфигурации {config_name}"
            )
        
        # Вызываем функцию плагина
        result = await plugin_manager.call_plugin_function(
            request.plugin_name,
            request.function_name,
            config_name,
            **request.params
        )
        
        return PluginCallResponse(
            success=True,
            result=result
        )
        
    except Exception as e:
        return PluginCallResponse(
            success=False,
            result=None,
            error=str(e)
        )

@router.post("/custom", response_model=PluginCallResponse)
async def call_custom_plugin(
    request: PluginCallRequest,
    config_name: str
):
    """
    Универсальный эндпоинт для вызова любого плагина
    """
    try:
        # Проверяем существование плагина
        if request.plugin_name not in plugin_manager.get_loaded_plugins(config_name):
            raise HTTPException(
                status_code=404,
                detail=f"Плагин {request.plugin_name} не найден в конфигурации {config_name}"
            )
        
        # Получаем функцию из плагина
        plugin_func = plugin_manager.get_plugin_function(
            request.plugin_name, 
            request.function_name,
            config_name
        )
        
        if not plugin_func:
            raise HTTPException(
                status_code=404, 
                detail=f"Функция {request.function_name} не найдена в плагине {request.plugin_name} для конфигурации {config_name}"
            )
        
        # Вызываем функцию плагина
        result = await plugin_manager.call_plugin_function(
            request.plugin_name,
            request.function_name,
            config_name,
            **request.params
        )
        
        return PluginCallResponse(
            success=True,
            result=result
        )
        
    except Exception as e:
        return PluginCallResponse(
            success=False,
            result=None,
            error=str(e)
        )

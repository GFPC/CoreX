"""
Plugin API for GFP CoreX.
Provides access to core system functions for plugins.
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional

import requests

from ..core.config import get_config
from ..core.database import commit_and_close_session, get_session_auto_cleanup


class PluginAPI:
    """API for plugins to access core system functions."""
    
    def __init__(self, config_name: str):
        self.config_name = config_name
        self.config = get_config(config_name)
    
    async def send_notification(self, user_id: int, message: str, channel: str = "email") -> bool:
        """
        Send notification to user.
        
        Args:
            user_id: User ID
            message: Notification message
            channel: Notification channel (email, telegram, etc.)
            
        Returns:
            bool: True if notification sent successfully
        """
        try:
            # Get user data
            session = await get_session_auto_cleanup(self.config_name, self.config)
            try:
                result = await session.execute(
                    f"SELECT email, username FROM users WHERE id = {user_id}"
                )
                user = result.fetchone()
                
                if not user:
                    print(f"❌ User {user_id} not found")
                    return False
                
                # Send notification based on channel
                if channel == "email":
                    return await self._send_email_notification(user[0], message)
                elif channel == "telegram":
                    return await self._send_email_notification(user_id, message)
                else:
                    print(f"❌ Unknown notification channel: {channel}")
                    return False
            finally:
                await commit_and_close_session(session)
                    
        except Exception as e:
            print(f"❌ Error sending notification: {e}")
            return False
    
    async def get_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user data.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict or None: User data
        """
        try:
            session = await get_session_auto_cleanup(self.config_name, self.config)
            try:
                result = await session.execute(
                    f"SELECT id, username, email, first_name, last_name, role_id FROM users WHERE id = {user_id}"
                )
                user = result.fetchone()
                
                if user:
                    return {
                        "id": user[0],
                        "username": user[1],
                        "email": user[2],
                        "first_name": user[3],
                        "last_name": user[4],
                        "role_id": user[5]
                    }
                return None
            finally:
                await commit_and_close_session(session)
                
        except Exception as e:
            print(f"❌ Error getting user data: {e}")
            return None
    
    async def call_external_api(self, url: str, method: str = "GET", data: Dict = None, headers: Dict = None) -> Optional[Dict[str, Any]]:
        """
        Call external API.
        
        Args:
            url: API URL
            method: HTTP method
            data: Request data
            headers: Request headers
            
        Returns:
            Dict or None: API response
        """
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=headers)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, headers=headers)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                print(f"❌ Unsupported HTTP method: {method}")
                return None
            
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            }
            
        except Exception as e:
            print(f"❌ Error calling external API: {e}")
            return None
    
    async def log_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """
        Log event to system logs.
        
        Args:
            event_type: Type of event
            data: Event data
            
        Returns:
            bool: True if logged successfully
        """
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "data": data,
                "plugin": "user_plugin"
            }
            
            print(f"📝 [PLUGIN LOG] {event_type}: {json.dumps(data, indent=2)}")
            return True
            
        except Exception as e:
            print(f"❌ Error logging event: {e}")
            return False
    
    async def schedule_task(self, task_name: str, delay_seconds: int, task_data: Dict = None) -> bool:
        """
        Schedule a task for later execution.
        
        Args:
            task_name: Name of the task
            delay_seconds: Delay in seconds
            task_data: Task data
            
        Returns:
            bool: True if scheduled successfully
        """
        try:
            # Simple task scheduling (in production would use Celery or similar)
            print(f"⏰ Scheduled task '{task_name}' for {delay_seconds} seconds from now")
            
            # Store task info (in production would store in database)
            task_info = {
                "name": task_name,
                "scheduled_at": datetime.now().isoformat(),
                "execute_at": (datetime.now().timestamp() + delay_seconds),
                "data": task_data or {}
            }
            
            return True
            
        except Exception as e:
            print(f"❌ Error scheduling task: {e}")
            return False
    
    async def get_plugin_data(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get data stored by plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Dict or None: Plugin data
        """
        try:
            # In production, this would query a plugin_data table
            # For now, return empty dict
            return {}
            
        except Exception as e:
            print(f"❌ Error getting plugin data: {e}")
            return None
    
    async def set_plugin_data(self, plugin_name: str, data: Dict[str, Any]) -> bool:
        """
        Store data for plugin.
        
        Args:
            plugin_name: Name of the plugin
            data: Data to store
            
        Returns:
            bool: True if stored successfully
        """
        try:
            # In production, this would store in a plugin_data table
            print(f"💾 Stored data for plugin '{plugin_name}': {json.dumps(data, indent=2)}")
            return True
            
        except Exception as e:
            print(f"❌ Error setting plugin data: {e}")
            return False
    
    async def _send_email_notification(self, email: str, message: str) -> bool:
        """Send email notification (placeholder)."""
        print(f"📧 [EMAIL] To: {email}, Message: {message}")
        return True
    
    async def _send_telegram_notification(self, user_id: int, message: str) -> bool:
        """Send Telegram notification (placeholder)."""
        print(f"📱 [TELEGRAM] To user {user_id}, Message: {message}")
        return True


# Global plugin API instance
def get_plugin_api(config_name: str) -> PluginAPI:
    """Get plugin API instance for configuration."""
    return PluginAPI(config_name) 
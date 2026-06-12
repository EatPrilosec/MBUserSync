"""Emby and Jellyfin API client (compatible API)."""
import httpx
import logging
from typing import List, Dict, Optional, Any
from backend.clients.base import BaseMediaServerClient
from backend.models.schemas import UserSchema, ServerType

logger = logging.getLogger(__name__)


class EmbyJellyfinClient(BaseMediaServerClient):
    """Client for Emby/Jellyfin API (v2 - compatible)."""
    
    def _build_base_url(self) -> str:
        """Build base URL for Emby/Jellyfin."""
        return f"http://{self.host}:{self.port}/emby"
    
    async def test_connection(self) -> tuple[bool, str]:
        """Test connection to Emby/Jellyfin server."""
        try:
            client = await self._get_client()
            headers = {"X-MediaBrowser-Token": self.api_key}
            response = await client.get(f"{self.base_url}/Users", headers=headers, timeout=10)
            
            if response.status_code == 200:
                users = response.json()
                return True, f"Connected. Found {len(users)} users."
            else:
                return False, f"Connection failed: HTTP {response.status_code}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    async def get_users(self) -> List[UserSchema]:
        """Get list of users from Emby/Jellyfin."""
        try:
            client = await self._get_client()
            headers = {"X-MediaBrowser-Token": self.api_key}
            response = await client.get(f"{self.base_url}/Users", headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Emby: Failed to get users: HTTP {response.status_code}")
                return []
            
            users = response.json()
            result = []
            
            for user in users:
                result.append(UserSchema(
                    id=user.get("Id"),
                    username=user.get("Name"),
                    email=user.get("PrimaryImageTag"),  # Not exactly email, but field available
                    server=ServerType.EMBY,
                    is_admin=user.get("Policy", {}).get("IsAdministrator", False),
                    is_disabled=user.get("Policy", {}).get("IsDisabled", False),
                    extra_data={"policy": user.get("Policy", {})}
                ))
            
            return result
        except Exception as e:
            logger.error(f"Emby: Error getting users: {str(e)}")
            return []
    
    async def create_user(self, username: str, password: str = "ChangeMe123!") -> tuple[bool, Optional[str], Optional[str]]:
        """Create a new user in Emby/Jellyfin."""
        try:
            client = await self._get_client()
            headers = {"X-MediaBrowser-Token": self.api_key}
            payload = {
                "Name": username,
                "Password": password
            }
            
            response = await client.post(
                f"{self.base_url}/Users/New",
                headers=headers,
                json=payload
            )
            
            if response.status_code in [200, 201]:
                user_data = response.json()
                return True, user_data.get("Id"), None
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Emby: Failed to create user {username}: {error_msg}")
                return False, None, error_msg
        except Exception as e:
            logger.error(f"Emby: Error creating user {username}: {str(e)}")
            return False, None, str(e)
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserSchema]:
        """Get user by ID from Emby/Jellyfin."""
        try:
            client = await self._get_client()
            headers = {"X-MediaBrowser-Token": self.api_key}
            response = await client.get(f"{self.base_url}/Users/{user_id}", headers=headers)
            
            if response.status_code != 200:
                logger.warning(f"Emby: User {user_id} not found")
                return None
            
            user = response.json()
            return UserSchema(
                id=user.get("Id"),
                username=user.get("Name"),
                server=ServerType.EMBY,
                is_admin=user.get("Policy", {}).get("IsAdministrator", False),
                is_disabled=user.get("Policy", {}).get("IsDisabled", False),
                extra_data={"policy": user.get("Policy", {})}
            )
        except Exception as e:
            logger.error(f"Emby: Error getting user {user_id}: {str(e)}")
            return None
    
    async def get_user_template(self, template_username: str) -> Optional[Dict[str, Any]]:
        """Get template user policy/settings."""
        try:
            client = await self._get_client()
            headers = {"X-MediaBrowser-Token": self.api_key}
            
            # Get users list
            response = await client.get(f"{self.base_url}/Users", headers=headers)
            if response.status_code != 200:
                return None
            
            users = response.json()
            template_user = next((u for u in users if u.get("Name") == template_username), None)
            
            if template_user:
                return template_user.get("Policy", {})
            
            return None
        except Exception as e:
            logger.error(f"Emby: Error getting template user {template_username}: {str(e)}")
            return None
    
    async def update_user_from_template(self, user_id: str, template_data: Dict[str, Any]) -> tuple[bool, str]:
        """Update user policy from template."""
        try:
            client = await self._get_client()
            headers = {"X-MediaBrowser-Token": self.api_key}
            
            response = await client.post(
                f"{self.base_url}/Users/{user_id}/Policy",
                headers=headers,
                json=template_data
            )
            
            if response.status_code in [200, 204]:
                return True, "User policy updated from template"
            else:
                error_msg = f"HTTP {response.status_code}"
                logger.error(f"Emby: Failed to update user {user_id} policy: {error_msg}")
                return False, error_msg
        except Exception as e:
            logger.error(f"Emby: Error updating user {user_id}: {str(e)}")
            return False, str(e)

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
    
    async def delete_user(self, user_id: str) -> tuple[bool, str]:
        """Delete a user in Emby/Jellyfin."""
        try:
            client = await self._get_client()
            headers = {"X-MediaBrowser-Token": self.api_key}
            
            response = await client.delete(
                f"{self.base_url}/Users/{user_id}",
                headers=headers
            )
            
            if response.status_code in [200, 204]:
                return True, f"User {user_id} deleted successfully"
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Emby: Failed to delete user {user_id}: {error_msg}")
                return False, error_msg
        except Exception as e:
            logger.error(f"Emby: Error deleting user {user_id}: {str(e)}")
            return False, str(e)
            
    async def get_user_by_id(self, user_id: str) -> Optional[UserSchema]:
        """Get user by ID from Emby/Jellyfin."""
        try:
            client = await self._get_client()
            headers = {"X-MediaBrowser-Token": self.api_key}
            
            response = await client.get(
                f"{self.base_url}/Users/{user_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return UserSchema(
                    id=user_data["Id"],
                    username=user_data["Name"],
                    server=ServerType.EMBY,
                    is_admin=user_data.get("Policy", {}).get("IsAdministrator", False),
                    is_disabled=user_data.get("Policy", {}).get("IsDisabled", False),
                    extra_data=user_data
                )
            return None
        except Exception as e:
            logger.error(f"Emby: Error getting user {user_id}: {str(e)}")
            return None

    async def change_password(self, user_id: str, new_password: str) -> tuple[bool, str]:
        """Change user password in Emby/Jellyfin."""
        try:
            client = await self._get_client()
            headers = {"X-MediaBrowser-Token": self.api_key}
            
            # For admin changing another user's password, we typically post to /Users/{Id}/Password
            payload = {
                "CurrentPw": "", 
                "NewPw": new_password
            }
            
            response = await client.post(
                f"{self.base_url}/Users/{user_id}/Password",
                headers=headers,
                json=payload
            )
            
            if response.status_code in [200, 204]:
                return True, "Password updated successfully"
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Emby: Failed to change password for user {user_id}: {error_msg}")
                return False, error_msg
        except Exception as e:
            logger.error(f"Emby: Error changing password for user {user_id}: {str(e)}")
            return False, str(e)
    
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
            target_lower = template_username.lower()
            template_user = next((u for u in users if u.get("Name", "").lower() == target_lower), None)
            if template_user:
                template_id = template_user.get("Id")
                
                # Fetch DisplayPreferences for common web clients and views
                display_prefs_list = []
                if template_id:
                    # 'displaypreferences' = default (Emby), 'home' = Jellyfin home view
                    # '3ce5b65d-e116-d731-65d1-efc4a30ec35c' = Jellyfin Web client magic UUID for Home Layout
                    # '4a1707f1-0ac8-98fd-e56d-8ae52391872f' = Jellyfin Web client magic UUID for displaypreferences
                    known_ids = ["displaypreferences", "home", "3ce5b65d-e116-d731-65d1-efc4a30ec35c", "4a1707f1-0ac8-98fd-e56d-8ae52391872f"]
                    
                    for display_id in known_ids:
                        for client_str in ["web", "emby", "jellyfin-web"]:
                            try:
                                dp_resp = await client.get(
                                    f"{self.base_url}/DisplayPreferences/{display_id}?userId={template_id}&client={client_str}",
                                    headers=headers
                                )
                                if dp_resp.status_code == 200:
                                    dp_data = dp_resp.json()
                                    # Only add if we actually have data (not completely empty)
                                    # Keep original ID because Jellyfin requires it to match the view
                                    if dp_data:
                                        dp_data["Client"] = client_str
                                        # To avoid duplicates if Jellyfin returns same object for 'displaypreferences' and its UUID
                                        if not any(d.get("Id") == dp_data.get("Id") and d.get("Client") == client_str for d in display_prefs_list):
                                            display_prefs_list.append(dp_data)
                            except Exception as e:
                                logger.error(f"Emby: Failed to get DisplayPreferences ({display_id}) for {client_str}: {e}")

                return {
                    "Policy": template_user.get("Policy", {}),
                    "Configuration": template_user.get("Configuration", {}),
                    "DisplayPreferencesList": display_prefs_list
                }
            
            return None
        except Exception as e:
            logger.error(f"Emby: Error getting template user {template_username}: {str(e)}")
            return None
    
    async def update_user_from_template(self, user_id: str, template_data: Dict[str, Any]) -> tuple[bool, str]:
        """Update user policy and configuration from template."""
        try:
            client = await self._get_client()
            headers = {"X-MediaBrowser-Token": self.api_key}
            
            # Post Policy
            policy_data = template_data.get("Policy", template_data)
            policy_response = await client.post(
                f"{self.base_url}/Users/{user_id}/Policy",
                headers=headers,
                json=policy_data
            )
            
            # Post Configuration if available
            config_data = template_data.get("Configuration")
            config_success = True
            if config_data:
                config_response = await client.post(
                    f"{self.base_url}/Users/{user_id}/Configuration",
                    headers=headers,
                    json=config_data
                )
                if config_response.status_code not in [200, 204]:
                    config_success = False
                    logger.error(f"Emby: Failed to update configuration for {user_id}")
            
            # Post DisplayPreferences if available
            dp_list = template_data.get("DisplayPreferencesList", [])
            for dp_data in dp_list:
                client_str = dp_data.get("Client", "web")
                # Use the original Id if present, otherwise default to 'displaypreferences'
                display_id = dp_data.get("Id", "displaypreferences")
                try:
                    dp_response = await client.post(
                        f"{self.base_url}/DisplayPreferences/{display_id}?userId={user_id}&client={client_str}",
                        headers=headers,
                        json=dp_data
                    )
                    if dp_response.status_code not in [200, 204]:
                        logger.error(f"Emby: Failed to update display preferences ({display_id}) for {user_id}")
                except Exception as e:
                    logger.error(f"Emby: Error updating display preferences ({display_id}) for {user_id}: {e}")
            
            if policy_response.status_code in [200, 204] and config_success:
                return True, "User policy, configuration, and display preferences updated from template"
            else:
                error_msg = f"HTTP {policy_response.status_code}" if not config_success else f"HTTP {policy_response.status_code}"
                logger.error(f"Emby: Failed to fully update user {user_id} from template")
                return False, error_msg
        except Exception as e:
            logger.error(f"Emby: Error updating user {user_id}: {str(e)}")
            return False, str(e)

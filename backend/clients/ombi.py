"""Ombi API client."""
import httpx
import logging
from typing import List, Dict, Optional, Any
from backend.clients.base import BaseMediaServerClient
from backend.models.schemas import UserSchema, ServerType

logger = logging.getLogger(__name__)


class OmbiClient(BaseMediaServerClient):
    """Client for Ombi API (v4)."""
    
    def _build_base_url(self) -> str:
        """Build base URL for Ombi."""
        return f"http://{self.host}:{self.port}/api/v1"
    
    async def test_connection(self) -> tuple[bool, str]:
        """Test connection to Ombi server."""
        try:
            client = await self._get_client()
            headers = {"ApiKey": self.api_key}
            response = await client.get(f"{self.base_url}/Identity/Users", headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                total = len(data) if isinstance(data, list) else 0
                return True, f"Connected. Found {total} users."
            else:
                return False, f"Connection failed: HTTP {response.status_code}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    async def get_users(self) -> List[UserSchema]:
        """Get list of users from Ombi."""
        try:
            client = await self._get_client()
            headers = {"ApiKey": self.api_key}
            
            response = await client.get(f"{self.base_url}/Identity/Users", headers=headers)
            if response.status_code != 200:
                logger.error(f"Ombi: Failed to get users: HTTP {response.status_code}")
                return []
            
            page_users = response.json()
            if not isinstance(page_users, list):
                return []
            
            users = []
            for user in page_users:
                is_admin = any(c.get("value") == "Admin" and c.get("enabled", False) for c in user.get("claims", []))
                uname = user.get("alias") or user.get("userName") or ""
                if "@" in uname:
                    uname = uname.split("@")[0]
                    
                users.append(UserSchema(
                    id=user.get("id"),
                    username=uname,
                    email=user.get("emailAddress"),
                    server=ServerType.OMBI,
                    is_admin=is_admin,
                    is_disabled=False,
                    extra_data={"roles": user.get("claims", [])}
                ))
            
            return users
        except Exception as e:
            logger.error(f"Ombi: Error getting users: {str(e)}")
            return []
    
    async def create_user(self, username: str, password: str = "ChangeMe123!") -> tuple[bool, Optional[str], Optional[str]]:
        """Create a new user in Ombi."""
        try:
            client = await self._get_client()
            headers = {"ApiKey": self.api_key}
            payload = {
                "userName": username,
                "password": password,
                "emailAddress": "",
                "claims": []
            }
            
            response = await client.post(
                f"{self.base_url}/Identity",
                headers=headers,
                json=payload
            )
            
            if response.status_code in [200, 201]:
                user_data = response.json()
                user_id = user_data.get("id")
                if not user_id:
                    # Ombi v4 returns {"successful": true, "errors": null} without an ID
                    # We must fetch the user list to find the ID of the newly created user
                    users_resp = await client.get(f"{self.base_url}/Identity/Users", headers=headers)
                    if users_resp.status_code == 200:
                        for u in users_resp.json():
                            if u.get("userName") == username:
                                user_id = u.get("id")
                                break
                return True, user_id, None
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Ombi: Failed to create user {username}: {error_msg}")
                return False, None, error_msg
        except Exception as e:
            logger.error(f"Ombi: Error creating user {username}: {str(e)}")
            return False, None, str(e)
    
    async def delete_user(self, user_id: str) -> tuple[bool, str]:
        """Delete a user in Ombi."""
        try:
            client = await self._get_client()
            headers = {"ApiKey": self.api_key}
            
            response = await client.delete(
                f"{self.base_url}/Identity/{user_id}",
                headers=headers
            )
            
            if response.status_code in [200, 204]:
                return True, f"User {user_id} deleted successfully"
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Ombi: Failed to delete user {user_id}: {error_msg}")
                return False, error_msg
        except Exception as e:
            logger.error(f"Ombi: Error deleting user {user_id}: {str(e)}")
            return False, str(e)
            
    async def get_user_by_id(self, user_id: str) -> Optional[UserSchema]:
        """Get user by ID from Ombi."""
        try:
            client = await self._get_client()
            headers = {"ApiKey": self.api_key}
            response = await client.get(f"{self.base_url}/Identity/User/{user_id}", headers=headers)
            
            if response.status_code != 200:
                logger.warning(f"Ombi: User {user_id} not found")
                return None
            
            user = response.json()
            is_admin = any(c.get("value") == "Admin" and c.get("enabled", False) for c in user.get("claims", []))
            uname = user.get("alias") or user.get("userName") or ""
            if "@" in uname:
                uname = uname.split("@")[0]
                
            return UserSchema(
                id=user.get("id"),
                username=uname,
                email=user.get("emailAddress"),
                server=ServerType.OMBI,
                is_admin=is_admin,
                is_disabled=False,
                extra_data=user
            )
        except Exception as e:
            logger.error(f"Ombi: Error getting user {user_id}: {str(e)}")
            return None

    async def change_password(self, user_id: str, new_password: str) -> tuple[bool, str]:
        """Change user password in Ombi."""
        try:
            client = await self._get_client()
            headers = {"ApiKey": self.api_key}
            
            response = await client.get(f"{self.base_url}/Identity/User/{user_id}", headers=headers)
            if response.status_code != 200:
                return False, "User not found"
                
            user = response.json()
            user["password"] = new_password
            
            response = await client.put(
                f"{self.base_url}/Identity",
                headers=headers,
                json=user
            )
            
            if response.status_code in [200, 204]:
                return True, "Password updated successfully"
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Ombi: Failed to change password for user {user_id}: {error_msg}")
                return False, error_msg
        except Exception as e:
            logger.error(f"Ombi: Error changing password for user {user_id}: {str(e)}")
            return False, str(e)
    
    async def get_user_template(self, template_username: str) -> Optional[Dict[str, Any]]:
        """Get template user settings (roles/claims)."""
        try:
            client = await self._get_client()
            headers = {"ApiKey": self.api_key}
            
            # Get users list
            response = await client.get(f"{self.base_url}/Identity/Users", headers=headers)
            if response.status_code != 200:
                return None
            
            users = response.json()
            if not isinstance(users, list):
                return None
                
            target_lower = template_username.lower()
            template_user = None
            
            for u in users:
                uname = u.get("alias") or u.get("userName") or ""
                if "@" in uname:
                    uname = uname.split("@")[0]
                if uname.lower() == target_lower:
                    template_user = u
                    break
            
            if template_user:
                # We need to strip any userId from the claims and quality profiles
                claims = template_user.get("claims", [])
                clean_claims = [{"value": c.get("value"), "enabled": c.get("enabled", False)} for c in claims]
                
                quality_profiles = template_user.get("userQualityProfiles") or {}
                clean_quality = {k: v for k, v in quality_profiles.items() if k not in ["userId", "id"]}
                
                return {
                    "claims": clean_claims,
                    "userQualityProfiles": clean_quality,
                    "movieRequestLimit": template_user.get("movieRequestLimit"),
                    "episodeRequestLimit": template_user.get("episodeRequestLimit"),
                    "musicRequestLimit": template_user.get("musicRequestLimit"),
                    "movieRequestQuota": template_user.get("movieRequestQuota"),
                    "episodeRequestQuota": template_user.get("episodeRequestQuota"),
                    "musicRequestQuota": template_user.get("musicRequestQuota"),
                    "movieRequestLimitType": template_user.get("movieRequestLimitType"),
                    "musicRequestLimitType": template_user.get("musicRequestLimitType"),
                    "episodeRequestLimitType": template_user.get("episodeRequestLimitType"),
                    "streamingCountry": template_user.get("streamingCountry"),
                    "language": template_user.get("language")
                }
            
            return None
        except Exception as e:
            logger.error(f"Ombi: Error getting template user {template_username}: {str(e)}")
            return None
    
    async def update_user_from_template(self, user_id: str, template_data: Dict[str, Any]) -> tuple[bool, str]:
        """Update user claims/roles from template."""
        try:
            client = await self._get_client()
            headers = {"ApiKey": self.api_key}
            
            # Get current user
            response = await client.get(f"{self.base_url}/Identity/User/{user_id}", headers=headers)
            if response.status_code != 200:
                return False, "Could not retrieve user"
            
            user = response.json()
            
            # Update with template data
            for key, value in template_data.items():
                if key == "userQualityProfiles":
                    target_qp = user.get("userQualityProfiles") or {}
                    for k, v in value.items():
                        target_qp[k] = v
                    user["userQualityProfiles"] = target_qp
                elif key == "claims":
                    user["claims"] = value
                else:
                    if value is not None:
                        user[key] = value
            
            response = await client.put(
                f"{self.base_url}/Identity",
                headers=headers,
                json=user
            )
            
            if response.status_code in [200, 204]:
                return True, "User updated from template"
            else:
                error_msg = f"HTTP {response.status_code}"
                logger.error(f"Ombi: Failed to update user {user_id}: {error_msg}")
                return False, error_msg
        except Exception as e:
            logger.error(f"Ombi: Error updating user {user_id}: {str(e)}")
            return False, str(e)

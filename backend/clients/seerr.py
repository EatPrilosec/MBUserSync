"""Seerr API client (Overseerr/Jellyseerr unified)."""
import httpx
import logging
from typing import List, Dict, Optional, Any
from backend.clients.base import BaseMediaServerClient
from backend.models.schemas import UserSchema, ServerType

logger = logging.getLogger(__name__)


class SeerrClient(BaseMediaServerClient):
    """Client for Seerr API (unified Overseerr/Jellyseerr)."""
    
    def _build_base_url(self) -> str:
        """Build base URL for Seerr."""
        return f"http://{self.host}:{self.port}/api/v1"
    
    async def test_connection(self) -> tuple[bool, str]:
        """Test connection to Seerr server."""
        try:
            client = await self._get_client()
            headers = {"X-Api-Key": self.api_key}
            response = await client.get(f"{self.base_url}/user?take=1", headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                total = data.get("pageInfo", {}).get("results", 0)
                return True, f"Connected. Found {total} users."
            else:
                return False, f"Connection failed: HTTP {response.status_code}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    async def get_users(self) -> List[UserSchema]:
        """Get list of users from Seerr."""
        try:
            client = await self._get_client()
            headers = {"X-Api-Key": self.api_key}
            
            users = []
            skip = 0
            take = 50
            
            while True:
                response = await client.get(
                    f"{self.base_url}/user?take={take}&skip={skip}",
                    headers=headers
                )
                
                if response.status_code != 200:
                    logger.error(f"Seerr: Failed to get users: HTTP {response.status_code}")
                    break
                
                data = response.json()
                page_users = data.get("results", [])
                
                if not page_users:
                    break
                
                for user in page_users:
                    permissions = user.get("permissions", 0)
                    uname = user.get("jellyfinUsername") or user.get("plexUsername") or user.get("username") or user.get("email", "")
                    if "@" in uname:
                        uname = uname.split("@")[0]
                        
                    users.append(UserSchema(
                        id=str(user.get("id")),
                        username=uname,
                        email=user.get("email"),
                        server=ServerType.SEERR,
                        is_admin=(permissions & 2) != 0,  # ADMIN flag is bit 1
                        is_disabled=False,  # Seerr doesn't have a disabled flag like others
                        extra_data={"permissions": permissions}
                    ))
                
                skip += take
                page_info = data.get("pageInfo", {})
                total_results = page_info.get("results", 0)
                if skip >= total_results:
                    break
            
            return users
        except Exception as e:
            logger.error(f"Seerr: Error getting users: {str(e)}")
            return []
    
    async def create_user(self, username: str, password: str = "ChangeMe123!") -> tuple[bool, Optional[str], Optional[str]]:
        """Create a new user in Seerr (note: Seerr uses email-based auth)."""
        try:
            import re
            client = await self._get_client()
            headers = {"X-Api-Key": self.api_key}
            
            # Seerr typically uses email as identifier
            # Sanitize username for email: strip characters invalid in email local part
            email_safe_name = re.sub(r"[^a-zA-Z0-9._\-+]", "", username)
            if not email_safe_name:
                email_safe_name = "user"
            email = username if "@" in username else f"{email_safe_name}@fale.ema.il"
            
            payload = {
                "email": email,
                "username": username,
                "password": password,
                "permissions": 0  # Regular user (no special permissions)
            }
            
            response = await client.post(
                f"{self.base_url}/user",
                headers=headers,
                json=payload
            )
            
            if response.status_code in [200, 201]:
                user_data = response.json()
                return True, str(user_data.get("id")), None
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Seerr: Failed to create user {username}: {error_msg}")
                return False, None, error_msg
        except Exception as e:
            logger.error(f"Seerr: Error creating user {username}: {str(e)}")
            return False, None, str(e)
    
    async def delete_user(self, user_id: str) -> tuple[bool, str]:
        """Delete a user in Seerr."""
        try:
            client = await self._get_client()
            headers = {"X-Api-Key": self.api_key}
            
            response = await client.delete(
                f"{self.base_url}/user/{user_id}",
                headers=headers
            )
            
            if response.status_code in [200, 204]:
                return True, f"User {user_id} deleted successfully"
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Seerr: Failed to delete user {user_id}: {error_msg}")
                return False, error_msg
        except Exception as e:
            logger.error(f"Seerr: Error deleting user {user_id}: {str(e)}")
            return False, str(e)
            
    async def get_user_by_id(self, user_id: str) -> Optional[UserSchema]:
        """Get user by ID from Seerr."""
        try:
            client = await self._get_client()
            headers = {"X-Api-Key": self.api_key}
            
            response = await client.get(
                f"{self.base_url}/user/{user_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                user_data = response.json()
                # Seerr priority name
                uname = user_data.get("plexUsername") or user_data.get("jellyfinUsername") or user_data.get("username") or user_data.get("email", "").split("@")[0]
                
                # Check for admin
                permissions = user_data.get("permissions", 0)
                is_admin = bool(permissions & 2) # 2 is ADMIN in Seerr
                
                return UserSchema(
                    id=user_data["id"],
                    username=uname,
                    email=user_data.get("email"),
                    server=ServerType.SEERR,
                    is_admin=is_admin,
                    is_disabled=False,
                    extra_data=user_data
                )
            return None
        except Exception as e:
            logger.error(f"Seerr: Error getting user {user_id}: {str(e)}")
            return None

    async def change_password(self, user_id: str, new_password: str) -> tuple[bool, str]:
        """Change user password in Seerr."""
        try:
            client = await self._get_client()
            headers = {"X-Api-Key": self.api_key}
            
            payload = {
                "password": new_password
            }
            
            response = await client.put(
                f"{self.base_url}/user/{user_id}",
                headers=headers,
                json=payload
            )
            
            if response.status_code in [200, 204]:
                return True, "Password updated successfully"
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Seerr: Failed to change password for user {user_id}: {error_msg}")
                return False, error_msg
        except Exception as e:
            logger.error(f"Seerr: Error changing password for user {user_id}: {str(e)}")
            return False, str(e)
    
    async def get_user_template(self, template_username: str) -> Optional[Dict[str, Any]]:
        """Get template user settings (permission level, etc.)."""
        try:
            client = await self._get_client()
            headers = {"X-Api-Key": self.api_key}
            
            # Get users list
            response = await client.get(f"{self.base_url}/user?take=100&skip=0", headers=headers)
            if response.status_code != 200:
                return None
            
            data = response.json()
            users = data.get("results", [])
            
            # Match by username or email
            template_user = next(
                (u for u in users if u.get("username") == template_username or u.get("email") == template_username),
                None
            )
            
            if template_user:
                return {
                    "permissions": template_user.get("permissions", 0)
                }
            
            return None
        except Exception as e:
            logger.error(f"Seerr: Error getting template user {template_username}: {str(e)}")
            return None
    
    async def update_user_from_template(self, user_id: str, template_data: Dict[str, Any]) -> tuple[bool, str]:
        """Update user permission level from template."""
        try:
            client = await self._get_client()
            headers = {"X-Api-Key": self.api_key}
            
            # Get current user
            response = await client.get(f"{self.base_url}/user/{user_id}", headers=headers)
            if response.status_code != 200:
                return False, "Could not retrieve user"
            
            user = response.json()
            
            # Update with template data
            user["permissions"] = template_data.get("permissions", user.get("permissions", 0))
            
            response = await client.put(
                f"{self.base_url}/user/{user_id}",
                headers=headers,
                json=user
            )
            
            if response.status_code in [200, 204]:
                return True, "User updated from template"
            else:
                error_msg = f"HTTP {response.status_code}"
                logger.error(f"Seerr: Failed to update user {user_id}: {error_msg}")
                return False, error_msg
        except Exception as e:
            logger.error(f"Seerr: Error updating user {user_id}: {str(e)}")
            return False, str(e)

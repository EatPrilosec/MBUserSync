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
                total = data.get("pageInfo", {}).get("totalPages", 0)
                return True, f"Connected. Found {total} pages of users."
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
                    users.append(UserSchema(
                        id=str(user.get("id")),
                        username=user.get("email", user.get("username", "")),
                        email=user.get("email"),
                        server=ServerType.SEERR,
                        is_admin=user.get("permissionLevel", 0) >= 2,
                        is_disabled=False,  # Seerr doesn't have a disabled flag like others
                        extra_data={"permissionLevel": user.get("permissionLevel", 0)}
                    ))
                
                skip += take
                page_info = data.get("pageInfo", {})
                if skip >= page_info.get("pages", 0) * page_info.get("pageSize", take):
                    break
            
            return users
        except Exception as e:
            logger.error(f"Seerr: Error getting users: {str(e)}")
            return []
    
    async def create_user(self, username: str, password: str = "ChangeMe123!") -> tuple[bool, Optional[str], Optional[str]]:
        """Create a new user in Seerr (note: Seerr uses email-based auth)."""
        try:
            client = await self._get_client()
            headers = {"X-Api-Key": self.api_key}
            
            # Seerr typically uses email as identifier
            email = username if "@" in username else f"{username}@local"
            
            payload = {
                "email": email,
                "username": username,
                "permissionLevel": 0  # Regular user
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
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserSchema]:
        """Get user by ID from Seerr."""
        try:
            client = await self._get_client()
            headers = {"X-Api-Key": self.api_key}
            response = await client.get(f"{self.base_url}/user/{user_id}", headers=headers)
            
            if response.status_code != 200:
                logger.warning(f"Seerr: User {user_id} not found")
                return None
            
            user = response.json()
            return UserSchema(
                id=str(user.get("id")),
                username=user.get("email", user.get("username", "")),
                email=user.get("email"),
                server=ServerType.SEERR,
                is_admin=user.get("permissionLevel", 0) >= 2,
                is_disabled=False,
                extra_data={"permissionLevel": user.get("permissionLevel", 0)}
            )
        except Exception as e:
            logger.error(f"Seerr: Error getting user {user_id}: {str(e)}")
            return None
    
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
                    "permissionLevel": template_user.get("permissionLevel", 0)
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
            user["permissionLevel"] = template_data.get("permissionLevel", 0)
            
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

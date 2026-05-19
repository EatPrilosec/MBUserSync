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
            response = await client.get(f"{self.base_url}/user?take=1", headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                total = data.get("total", 0)
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
            
            users = []
            skip = 0
            take = 50
            
            while True:
                response = await client.get(
                    f"{self.base_url}/user?take={take}&skip={skip}",
                    headers=headers
                )
                
                if response.status_code != 200:
                    logger.error(f"Ombi: Failed to get users: HTTP {response.status_code}")
                    break
                
                data = response.json()
                page_users = data.get("data", [])
                
                if not page_users:
                    break
                
                for user in page_users:
                    users.append(UserSchema(
                        id=user.get("id"),
                        username=user.get("userName"),
                        email=user.get("email"),
                        server=ServerType.OMBI,
                        is_admin=user.get("isAdmin", False),
                        is_disabled=user.get("deleted", False),
                        extra_data={"roles": user.get("claims", [])}
                    ))
                
                skip += take
                if len(page_users) < take:
                    break
            
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
                "isAdmin": False
            }
            
            response = await client.post(
                f"{self.base_url}/user",
                headers=headers,
                json=payload
            )
            
            if response.status_code in [200, 201]:
                user_data = response.json()
                return True, user_data.get("id"), None
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Ombi: Failed to create user {username}: {error_msg}")
                return False, None, error_msg
        except Exception as e:
            logger.error(f"Ombi: Error creating user {username}: {str(e)}")
            return False, None, str(e)
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserSchema]:
        """Get user by ID from Ombi."""
        try:
            client = await self._get_client()
            headers = {"ApiKey": self.api_key}
            response = await client.get(f"{self.base_url}/user/{user_id}", headers=headers)
            
            if response.status_code != 200:
                logger.warning(f"Ombi: User {user_id} not found")
                return None
            
            user = response.json()
            return UserSchema(
                id=user.get("id"),
                username=user.get("userName"),
                email=user.get("email"),
                server=ServerType.OMBI,
                is_admin=user.get("isAdmin", False),
                is_disabled=user.get("deleted", False),
                extra_data={"roles": user.get("claims", [])}
            )
        except Exception as e:
            logger.error(f"Ombi: Error getting user {user_id}: {str(e)}")
            return None
    
    async def get_user_template(self, template_username: str) -> Optional[Dict[str, Any]]:
        """Get template user settings (roles/claims)."""
        try:
            client = await self._get_client()
            headers = {"ApiKey": self.api_key}
            
            # Get users list
            response = await client.get(f"{self.base_url}/user?take=100&skip=0", headers=headers)
            if response.status_code != 200:
                return None
            
            data = response.json()
            users = data.get("data", [])
            template_user = next((u for u in users if u.get("userName") == template_username), None)
            
            if template_user:
                return {
                    "claims": template_user.get("claims", []),
                    "isAdmin": template_user.get("isAdmin", False)
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
            response = await client.get(f"{self.base_url}/user/{user_id}", headers=headers)
            if response.status_code != 200:
                return False, "Could not retrieve user"
            
            user = response.json()
            
            # Update with template data
            user["claims"] = template_data.get("claims", user.get("claims", []))
            user["isAdmin"] = template_data.get("isAdmin", False)
            
            response = await client.put(
                f"{self.base_url}/user/{user_id}",
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

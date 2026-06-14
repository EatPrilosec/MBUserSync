"""API clients for media servers."""
import httpx
import logging
from typing import List, Dict, Optional, Any
from backend.models.schemas import UserSchema, ServerType

logger = logging.getLogger(__name__)


class BaseMediaServerClient:
    """Base class for media server API clients."""
    
    def __init__(self, host: str, port: int, api_key: str, timeout: float = 30.0):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = self._build_base_url()
        self._client: Optional[httpx.AsyncClient] = None
    
    def _build_base_url(self) -> str:
        """Build base URL for API."""
        raise NotImplementedError
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    async def test_connection(self) -> tuple[bool, str]:
        """Test connection to the server. Returns (success, message)."""
        raise NotImplementedError
    
    async def get_users(self) -> List[UserSchema]:
        """Get list of users from the server."""
        raise NotImplementedError
    
    async def create_user(self, username: str, password: str = "ChangeMe123!") -> tuple[bool, Optional[str], Optional[str]]:
        """Create a new user. Returns (success, user_id, error_message)."""
        raise NotImplementedError
        
    async def delete_user(self, user_id: str) -> tuple[bool, str]:
        """Delete a user. Returns (success, message)."""
        raise NotImplementedError
        
    async def change_password(self, user_id: str, new_password: str) -> tuple[bool, str]:
        """Change a user's password. Returns (success, message)."""
        raise NotImplementedError
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserSchema]:
        """Get user by ID."""
        raise NotImplementedError
    
    async def get_user_template(self, template_username: str) -> Optional[Dict[str, Any]]:
        """Get template user data for cloning settings."""
        raise NotImplementedError
    
    async def update_user_from_template(self, user_id: str, template_data: Dict[str, Any]) -> tuple[bool, str]:
        """Update user settings from template. Returns (success, message)."""
        raise NotImplementedError

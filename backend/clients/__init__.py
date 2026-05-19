"""API client manager for all media servers."""
import logging
from typing import Dict, Optional
from backend.clients.base import BaseMediaServerClient
from backend.clients.emby import EmbyJellyfinClient
from backend.clients.ombi import OmbiClient
from backend.clients.seerr import SeerrClient
from backend.models.schemas import ServerType, ServerConfigSchema

logger = logging.getLogger(__name__)


class APIClientManager:
    """Manages lifecycle of all media server API clients."""
    
    def __init__(self):
        self.clients: Dict[ServerType, Optional[BaseMediaServerClient]] = {
            ServerType.EMBY: None,
            ServerType.JELLYFIN: None,
            ServerType.OMBI: None,
            ServerType.SEERR: None,
        }
    
    def get_or_create_client(self, server_type: ServerType, config: ServerConfigSchema) -> Optional[BaseMediaServerClient]:
        """Get existing client or create new one."""
        if not config.enabled:
            logger.warning(f"Server {server_type} is disabled")
            return None
        
        if server_type == ServerType.EMBY:
            return EmbyJellyfinClient(config.host, config.port, config.api_key)
        elif server_type == ServerType.JELLYFIN:
            return EmbyJellyfinClient(config.host, config.port, config.api_key)
        elif server_type == ServerType.OMBI:
            return OmbiClient(config.host, config.port, config.api_key)
        elif server_type == ServerType.SEERR:
            return SeerrClient(config.host, config.port, config.api_key)
        
        return None
    
    async def close_all(self) -> None:
        """Close all client connections."""
        for client in self.clients.values():
            if client is not None:
                await client.close()
        
        # Clear all clients
        for server_type in self.clients:
            self.clients[server_type] = None

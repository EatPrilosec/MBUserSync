"""User sync engine - core sync logic."""
import logging
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from backend.clients.base import BaseMediaServerClient
from backend.models.schemas import (
    UserSchema, SyncModeEnum, ServerType, ServerConfigSchema, UserSyncResultSchema
)

logger = logging.getLogger(__name__)


class UserSyncEngine:
    """Core engine for syncing users between media servers."""
    
    def __init__(self):
        self.last_sync_time: Optional[datetime] = None
        self.is_syncing: bool = False
    
    def _parse_exclude_list(self, exclude_str: str) -> Set[str]:
        """Parse comma-separated exclude list into set of usernames."""
        if not exclude_str:
            return set()
        return {u.strip().lower() for u in exclude_str.split(",") if u.strip()}
    
    def _add_default_exclusions(self, exclude_set: Set[str]) -> Set[str]:
        """Add common system/admin usernames to exclusion set."""
        default_exclusions = {
            "administrator",
            "admin",
            "system",
            "guest",
            "root",
            "daemon",
            "bin",
            "sync",
        }
        return exclude_set.union(default_exclusions)
    
    def _should_exclude_user(self, username: str, exclude_list: Set[str]) -> bool:
        """Check if user should be excluded from sync."""
        return username.lower() in exclude_list
    
    async def sync_primary_source(
        self,
        servers: Dict[ServerType, tuple[BaseMediaServerClient, ServerConfigSchema]],
    ) -> UserSyncResultSchema:
        """
        Sync users from primary source to all other enabled servers.
        
        PRIMARY_SOURCE mode: One server is marked as primary; all users on the primary
        are ensured to exist on secondary servers. Users not on primary are NOT removed
        from secondary servers.
        """
        self.is_syncing = True
        
        try:
            # Find primary server
            primary_server = None
            primary_client = None
            secondary_servers = []
            
            for server_type, (client, config) in servers.items():
                if config.is_primary:
                    primary_server = server_type
                    primary_client = client
                elif config.enabled:
                    secondary_servers.append((server_type, client, config))
            
            if primary_server is None or primary_client is None:
                return UserSyncResultSchema(
                    success=False,
                    message="No primary server configured",
                    errors=["PRIMARY_SOURCE mode requires a primary server to be set"]
                )
            
            if not secondary_servers:
                return UserSyncResultSchema(
                    success=False,
                    message="No secondary servers enabled",
                    errors=["At least one secondary server must be enabled"]
                )
            
            logger.info(f"Starting PRIMARY_SOURCE sync from {primary_server}")
            
            # Get users from primary
            primary_users = await primary_client.get_users()
            primary_config = servers[primary_server][1]
            primary_exclude = self._add_default_exclusions(
                self._parse_exclude_list(primary_config.exclude_list)
            )
            
            # Filter excluded users
            sync_users = [
                u for u in primary_users
                if not self._should_exclude_user(u.username, primary_exclude)
            ]
            
            logger.info(f"Primary server {primary_server}: {len(primary_users)} total users, "
                       f"{len(sync_users)} to sync")
            
            synced_count = 0
            errors = []
            details = {"primary": primary_server, "synced_users": []}
            
            # Sync to each secondary
            for sec_server_type, sec_client, sec_config in secondary_servers:
                logger.info(f"Syncing to {sec_server_type}...")
                
                sec_exclude = self._add_default_exclusions(
                    self._parse_exclude_list(sec_config.exclude_list)
                )
                
                # Get current users on secondary
                sec_users = await sec_client.get_users()
                sec_usernames = {u.username.lower() for u in sec_users}
                
                # Get template if configured
                template_data = None
                if sec_config.template_user:
                    template_data = await sec_client.get_user_template(sec_config.template_user)
                
                for user in sync_users:
                    # Skip if excluded on secondary
                    if self._should_exclude_user(user.username, sec_exclude):
                        logger.debug(f"User {user.username} excluded on {sec_server_type}")
                        continue
                    
                    # Check if user exists
                    if user.username.lower() in sec_usernames:
                        logger.debug(f"User {user.username} already exists on {sec_server_type}")
                        continue
                    
                    # Create user
                    success, user_id, error = await sec_client.create_user(user.username)
                    
                    if not success:
                        error_msg = f"Failed to create {user.username} on {sec_server_type}: {error}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        continue
                    
                    synced_count += 1
                    details["synced_users"].append({
                        "username": user.username,
                        "source": primary_server,
                        "destination": sec_server_type,
                        "user_id": user_id
                    })
                    
                    # Apply template if available
                    if template_data and user_id:
                        success, msg = await sec_client.update_user_from_template(user_id, template_data)
                        if not success:
                            logger.warning(f"Failed to apply template to {user.username} on {sec_server_type}: {msg}")
            
            self.last_sync_time = datetime.now()
            
            return UserSyncResultSchema(
                success=len(errors) == 0,
                message=f"Synced {synced_count} users from {primary_server}",
                synced_count=synced_count,
                errors=errors,
                details=details
            )
        
        finally:
            self.is_syncing = False
    
    async def sync_any_to_any(
        self,
        servers: Dict[ServerType, tuple[BaseMediaServerClient, ServerConfigSchema]],
    ) -> UserSyncResultSchema:
        """
        Sync users across all servers in a many-to-many fashion.
        
        ANY_TO_ANY mode: Collect all users from all enabled servers. Ensure each unique
        user exists on all other enabled servers. This creates a union of all users.
        """
        self.is_syncing = True
        
        try:
            if not servers:
                return UserSyncResultSchema(
                    success=False,
                    message="No servers configured",
                    errors=["At least one server must be configured"]
                )
            
            logger.info("Starting ANY_TO_ANY sync")
            
            # Collect all unique users from all servers
            all_users_by_server: Dict[ServerType, List[UserSchema]] = {}
            all_unique_usernames: Set[str] = set()
            
            for server_type, (client, config) in servers.items():
                exclude_set = self._add_default_exclusions(
                    self._parse_exclude_list(config.exclude_list)
                )
                
                users = await client.get_users()
                filtered_users = [
                    u for u in users
                    if not self._should_exclude_user(u.username, exclude_set)
                ]
                
                all_users_by_server[server_type] = filtered_users
                all_unique_usernames.update(u.username.lower() for u in filtered_users)
                
                logger.info(f"{server_type}: {len(users)} total, {len(filtered_users)} to sync")
            
            logger.info(f"Total unique users to sync: {len(all_unique_usernames)}")
            
            synced_count = 0
            errors = []
            details = {"mode": "any_to_any", "synced_users": []}
            
            # For each server, ensure all unique users exist
            for dest_server_type, (dest_client, dest_config) in servers.items():
                dest_users = all_users_by_server[dest_server_type]
                dest_usernames = {u.username.lower() for u in dest_users}
                
                dest_exclude = self._add_default_exclusions(
                    self._parse_exclude_list(dest_config.exclude_list)
                )
                
                # Get template if configured
                template_data = None
                if dest_config.template_user:
                    template_data = await dest_client.get_user_template(dest_config.template_user)
                
                for username in all_unique_usernames:
                    # Skip if excluded
                    if self._should_exclude_user(username, dest_exclude):
                        logger.debug(f"User {username} excluded on {dest_server_type}")
                        continue
                    
                    # Skip if already exists
                    if username in dest_usernames:
                        logger.debug(f"User {username} already exists on {dest_server_type}")
                        continue
                    
                    # Create user
                    success, user_id, error = await dest_client.create_user(username)
                    
                    if not success:
                        error_msg = f"Failed to create {username} on {dest_server_type}: {error}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        continue
                    
                    synced_count += 1
                    details["synced_users"].append({
                        "username": username,
                        "destination": dest_server_type,
                        "user_id": user_id
                    })
                    
                    # Apply template if available
                    if template_data and user_id:
                        success, msg = await dest_client.update_user_from_template(user_id, template_data)
                        if not success:
                            logger.warning(f"Failed to apply template to {username} on {dest_server_type}: {msg}")
            
            self.last_sync_time = datetime.now()
            
            return UserSyncResultSchema(
                success=len(errors) == 0,
                message=f"Synced {synced_count} users across {len(servers)} servers",
                synced_count=synced_count,
                errors=errors,
                details=details
            )
        
        finally:
            self.is_syncing = False


# Global sync engine instance
_sync_engine: Optional[UserSyncEngine] = None


def get_sync_engine() -> UserSyncEngine:
    """Get or create the global sync engine."""
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = UserSyncEngine()
    return _sync_engine

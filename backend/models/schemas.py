from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class SyncModeEnum(str, Enum):
    PRIMARY_SOURCE = "primary_source"
    ANY_TO_ANY = "any_to_any"


class ServerType(str, Enum):
    EMBY = "emby"
    JELLYFIN = "jellyfin"
    OMBI = "ombi"
    SEERR = "seerr"


class ServerConfigSchema(BaseModel):
    """Configuration for a single media server."""
    enabled: bool = False
    host: str = ""
    port: int = 8096
    api_key: str = ""
    is_primary: bool = False
    exclude_list: str = ""  # Comma-separated usernames
    template_user: Optional[str] = None  # Username to clone settings from


class SyncStatusSchema(BaseModel):
    """Current sync status."""
    enabled: bool
    last_sync_time: Optional[str] = None
    next_sync_time: Optional[str] = None
    sync_mode: SyncModeEnum
    last_sync_result: Optional[Dict[str, Any]] = None
    is_running: bool = False


class SyncConfigSchema(BaseModel):
    """Sync configuration."""
    sync_mode: SyncModeEnum = SyncModeEnum.PRIMARY_SOURCE
    sync_enabled: bool = True
    cron_schedule: str = "*/20 * * * *"  # Every 20 minutes
    password_strategy: str = "use_username"
    global_password: str = ""
    allow_blank_passwords: bool = False


class AppSettingsSchema(BaseModel):
    """Overall application settings."""
    servers: Dict[ServerType, ServerConfigSchema]
    sync_config: SyncConfigSchema


class UserSyncResultSchema(BaseModel):
    """Result of a user sync operation."""
    success: bool
    message: str
    synced_count: int = 0
    errors: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class ServerTestResultSchema(BaseModel):
    """Result of testing a server connection."""
    connected: bool
    message: str
    user_count: Optional[int] = None
    error: Optional[str] = None


class UserSchema(BaseModel):
    """Representation of a user from a media server."""
    id: str
    username: str
    email: Optional[str] = None
    server: ServerType
    is_admin: bool = False
    is_disabled: bool = False
    extra_data: Dict[str, Any] = Field(default_factory=dict)

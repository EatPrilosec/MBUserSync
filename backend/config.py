"""Configuration management using Pydantic Settings."""
import json
import os
from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from backend.models.schemas import ServerConfigSchema, SyncConfigSchema, ServerType, SyncModeEnum


class AppSettings(BaseSettings):
    """Application settings loaded from environment and JSON config."""
    
    debug: bool = False
    log_level: str = "INFO"
    config_file: str = "config.json"
    
    # Sync defaults from env
    sync_enabled: bool = True
    sync_mode: SyncModeEnum = SyncModeEnum.PRIMARY_SOURCE
    sync_cron: str = "*/20 * * * *"  # Every 20 minutes
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class ConfigService:
    """Service for loading and saving application configuration."""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self._config: Optional[Dict] = None
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from JSON file. Create default if not exists."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    self._config = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error loading config file {self.config_path}: {e}")
                self._config = self._get_default_config()
        else:
            self._config = self._get_default_config()
            self._save_config()
    
    def _get_default_config(self) -> Dict:
        """Return default configuration template."""
        return {
            "servers": {
                "emby": {
                    "enabled": False,
                    "host": "localhost",
                    "port": 8096,
                    "api_key": "",
                    "is_primary": False,
                    "exclude_list": "",
                    "template_user": None
                },
                "jellyfin": {
                    "enabled": False,
                    "host": "localhost",
                    "port": 8096,
                    "api_key": "",
                    "is_primary": False,
                    "exclude_list": "",
                    "template_user": None
                },
                "ombi": {
                    "enabled": False,
                    "host": "localhost",
                    "port": 5000,
                    "api_key": "",
                    "is_primary": False,
                    "exclude_list": "",
                    "template_user": None
                },
                "seerr": {
                    "enabled": False,
                    "host": "localhost",
                    "port": 5055,
                    "api_key": "",
                    "is_primary": False,
                    "exclude_list": "",
                    "template_user": None
                }
            },
            "sync_config": {
                "sync_mode": "primary_source",
                "sync_enabled": True,
                "cron_schedule": "*/20 * * * *"
            }
        }
    
    def get_config(self) -> Dict:
        """Get current configuration."""
        if self._config is None:
            self._load_config()
        return self._config
    
    def get_server_config(self, server_type: str) -> Optional[ServerConfigSchema]:
        """Get configuration for a specific server."""
        config = self.get_config()
        if server_type in config.get("servers", {}):
            try:
                return ServerConfigSchema(**config["servers"][server_type])
            except Exception as e:
                print(f"Error parsing server config for {server_type}: {e}")
                return None
        return None
    
    def get_sync_config(self) -> SyncConfigSchema:
        """Get sync configuration."""
        config = self.get_config()
        sync_data = config.get("sync_config", {})
        try:
            return SyncConfigSchema(**sync_data)
        except Exception as e:
            print(f"Error parsing sync config: {e}")
            return SyncConfigSchema()
    
    def update_server_config(self, server_type: str, server_config: ServerConfigSchema) -> bool:
        """Update configuration for a specific server."""
        config = self.get_config()
        if "servers" not in config:
            config["servers"] = {}
        
        config["servers"][server_type] = server_config.model_dump()
        self._config = config
        return self._save_config()
    
    def update_sync_config(self, sync_config: SyncConfigSchema) -> bool:
        """Update sync configuration."""
        config = self.get_config()
        config["sync_config"] = sync_config.model_dump()
        self._config = config
        return self._save_config()
    
    def _save_config(self) -> bool:
        """Save configuration to JSON file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump(self._config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config file {self.config_path}: {e}")
            return False
    
    def validate_config(self) -> tuple[bool, list[str]]:
        """Validate current configuration. Returns (is_valid, list_of_errors)."""
        errors = []
        config = self.get_config()
        
        # Check that at most one primary server is configured
        primary_count = 0
        enabled_count = 0
        for server_name, server_cfg in config.get("servers", {}).items():
            if server_cfg.get("enabled", False):
                enabled_count += 1
                if server_cfg.get("is_primary", False):
                    primary_count += 1
        
        if enabled_count == 0:
            errors.append("At least one server must be enabled")
            
        sync_config = self.get_sync_config()
        if sync_config.sync_mode not in [SyncModeEnum.PRIMARY_SOURCE, SyncModeEnum.ANY_TO_ANY]:
            errors.append(f"Invalid sync mode: {sync_config.sync_mode}")
            
        # If primary_source mode, enforce primary server rules
        if sync_config.sync_mode == SyncModeEnum.PRIMARY_SOURCE:
            if primary_count > 1:
                errors.append("Only one server can be set as primary")
            if primary_count == 0:
                errors.append("PRIMARY_SOURCE sync mode requires a primary server to be set")
        
        return len(errors) == 0, errors


# Global config service instance
_config_service: Optional[ConfigService] = None


def get_config_service() -> ConfigService:
    """Get or create the global config service."""
    global _config_service
    if _config_service is None:
        settings = AppSettings()
        _config_service = ConfigService(config_path=settings.config_file)
    return _config_service

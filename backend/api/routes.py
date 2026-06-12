"""API routes for server management, sync control, and settings."""
import logging
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from datetime import datetime

from backend.config import get_config_service
from backend.models.schemas import (
    ServerConfigSchema, SyncConfigSchema, ServerType, 
    SyncStatusSchema, UserSyncResultSchema, ServerTestResultSchema
)
from backend.clients import APIClientManager
from backend.services.sync_engine import get_sync_engine

logger = logging.getLogger(__name__)


async def test_server_connection(server_type: ServerType, config: ServerConfigSchema) -> tuple[bool, str, int]:
    """Test connection to a server. Returns (success, message, user_count)."""
    if not config.enabled:
        return False, "Server is disabled", 0
    
    client_manager = APIClientManager()
    client = client_manager.get_or_create_client(server_type, config)
    
    if client is None:
        return False, "Could not create client", 0
    
    try:
        success, message = await client.test_connection()
        
        if success:
            users = await client.get_users()
            return True, message, len(users)
        else:
            return False, message, 0
    finally:
        await client_manager.close_all()


def setup_routes(app: FastAPI) -> None:
    """Set up all API routes."""
    
    config_service = get_config_service()
    sync_engine = get_sync_engine()
    
    # ===== Settings Endpoints =====
    
    @app.get("/api/settings", response_model=Dict)
    async def get_settings():
        """Get all application settings."""
        config = config_service.get_config()
        sync_config = config_service.get_sync_config()
        
        return {
            "servers": config.get("servers", {}),
            "sync_config": sync_config.model_dump(),
            "sync_status": {
                "last_sync_time": sync_engine.last_sync_time.isoformat() if sync_engine.last_sync_time else None,
                "is_syncing": sync_engine.is_syncing
            }
        }
    
    @app.put("/api/settings")
    async def update_settings(settings: Dict):
        """Update application settings."""
        try:
            if "sync_config" in settings:
                sync_config = SyncConfigSchema(**settings["sync_config"])
                config_service.update_sync_config(sync_config)
            
            return {"success": True, "message": "Settings updated"}
        except Exception as e:
            logger.error(f"Error updating settings: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
    
    # ===== Server Management Endpoints =====
    
    @app.get("/api/servers")
    async def list_servers():
        """Get all server configurations."""
        config = config_service.get_config()
        return config.get("servers", {})
    
    @app.get("/api/servers/{server_name}")
    async def get_server(server_name: str):
        """Get specific server configuration."""
        config = config_service.get_server_config(server_name)
        if config is None:
            raise HTTPException(status_code=404, detail=f"Server {server_name} not found")
        return config.model_dump()
    
    @app.put("/api/servers/{server_name}")
    async def update_server(server_name: str, server_config: ServerConfigSchema):
        """Update server configuration."""
        try:
            # Ensure only one primary
            if server_config.is_primary:
                current_config = config_service.get_config()
                for sname, scfg in current_config.get("servers", {}).items():
                    if sname != server_name and scfg.get("is_primary", False):
                        scfg["is_primary"] = False
                        sc = ServerConfigSchema(**scfg)
                        config_service.update_server_config(sname, sc)
            
            config_service.update_server_config(server_name, server_config)
            return {"success": True, "message": f"Server {server_name} updated"}
        except Exception as e:
            logger.error(f"Error updating server {server_name}: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.post("/api/servers/{server_name}/test", response_model=ServerTestResultSchema)
    async def test_server(server_name: str, config_override: Optional[ServerConfigSchema] = None):
        """Test connection to a server."""
        try:
            server_type = ServerType(server_name)
            config = config_override or config_service.get_server_config(server_name)
            
            if config is None:
                return ServerTestResultSchema(
                    connected=False,
                    message="Server not found"
                )
            
            success, message, user_count = await test_server_connection(server_type, config)
            
            return ServerTestResultSchema(
                connected=success,
                message=message,
                user_count=user_count if success else None,
                error=None if success else message
            )
        except Exception as e:
            logger.error(f"Error testing server {server_name}: {str(e)}")
            return ServerTestResultSchema(
                connected=False,
                message="Error testing connection",
                error=str(e)
            )
    
    @app.post("/api/servers/{server_name}/users")
    async def get_server_users(server_name: str):
        """Get users from a specific server."""
        try:
            server_type = ServerType(server_name)
            config = config_service.get_server_config(server_name)
            
            if config is None or not config.enabled:
                raise HTTPException(status_code=400, detail="Server not found or disabled")
            
            client_manager = APIClientManager()
            client = client_manager.get_or_create_client(server_type, config)
            
            if client is None:
                raise HTTPException(status_code=400, detail="Could not create client")
            
            try:
                users = await client.get_users()
                return {
                    "server": server_name,
                    "user_count": len(users),
                    "users": [u.model_dump() for u in users]
                }
            finally:
                await client_manager.close_all()
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid server: {server_name}")
        except Exception as e:
            logger.error(f"Error getting users from {server_name}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ===== Sync Control Endpoints =====
    
    @app.get("/api/sync/status", response_model=SyncStatusSchema)
    async def get_sync_status():
        """Get current sync status."""
        sync_config = config_service.get_sync_config()
        
        return SyncStatusSchema(
            enabled=sync_config.sync_enabled,
            last_sync_time=sync_engine.last_sync_time.isoformat() if sync_engine.last_sync_time else None,
            sync_mode=sync_config.sync_mode,
            is_running=sync_engine.is_syncing
        )
    
    @app.post("/api/sync/run", response_model=UserSyncResultSchema)
    async def run_sync():
        """Manually trigger a sync operation."""
        if sync_engine.is_syncing:
            raise HTTPException(status_code=409, detail="Sync already in progress")
        
        try:
            sync_config = config_service.get_sync_config()
            
            if not sync_config.sync_enabled:
                raise HTTPException(status_code=400, detail="Sync is disabled")
            
            # Build servers dict
            client_manager = APIClientManager()
            servers = {}
            
            for server_type in ServerType:
                config = config_service.get_server_config(server_type.value)
                if config and config.enabled:
                    client = client_manager.get_or_create_client(server_type, config)
                    if client:
                        servers[server_type] = (client, config)
            
            if not servers:
                raise HTTPException(status_code=400, detail="No enabled servers")
            
            # Run sync
            try:
                if sync_config.sync_mode.value == "primary_source":
                    result = await sync_engine.sync_primary_source(servers)
                else:  # any_to_any
                    result = await sync_engine.sync_any_to_any(servers)
                
                return result
            finally:
                await client_manager.close_all()
        
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error running sync: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.put("/api/sync/config")
    async def update_sync_config(config: SyncConfigSchema):
        """Update sync configuration."""
        try:
            from apscheduler.triggers.cron import CronTrigger
            try:
                CronTrigger.from_crontab(config.cron_schedule)
            except ValueError as e:
                raise ValueError(f"Invalid cron schedule: {str(e)}")
            
            config_service.update_sync_config(config)
            
            import backend.main
            if backend.main.scheduler:
                from backend.scheduler.tasks import setup_scheduler
                setup_scheduler(backend.main.scheduler)
                
            return {"success": True, "message": "Sync config updated"}
        except Exception as e:
            logger.error(f"Error updating sync config: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.post("/api/sync/validate")
    async def validate_sync():
        """Validate configuration and show what would sync (dry-run)."""
        try:
            is_valid, errors = config_service.validate_config()
            
            validation_result = {
                "valid": is_valid,
                "errors": errors,
                "warnings": []
            }
            
            if not is_valid:
                return validation_result
            
            # Additional validation checks
            sync_config = config_service.get_sync_config()
            enabled_servers = []
            primary_server = None
            
            for server_type in ServerType:
                config = config_service.get_server_config(server_type.value)
                if config and config.enabled:
                    enabled_servers.append(server_type.value)
                    if config.is_primary:
                        primary_server = server_type.value
            
            validation_result["enabled_servers"] = enabled_servers
            validation_result["sync_mode"] = sync_config.sync_mode.value
            validation_result["primary_server"] = primary_server
            
            if sync_config.sync_mode.value == "primary_source" and not primary_server:
                validation_result["warnings"].append("PRIMARY_SOURCE mode requires a primary server")
            
            return validation_result
        except Exception as e:
            logger.error(f"Error validating sync: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    logger.info("API routes set up")

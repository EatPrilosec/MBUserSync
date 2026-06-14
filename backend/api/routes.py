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
from backend.services.token_service import get_token_service

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
    
    # ===== User Management Endpoints =====
    
    @app.get("/api/users")
    async def get_all_aggregated_users():
        """Get aggregated list of all users across all servers."""
        try:
            client_manager = APIClientManager()
            servers = {}
            for server_type in ServerType:
                config = config_service.get_server_config(server_type.value)
                if config and config.enabled:
                    client = client_manager.get_or_create_client(server_type, config)
                    if client:
                        servers[server_type] = (client, config)
            
            all_users = {}
            try:
                for server_type, (client, config) in servers.items():
                    users = await client.get_users()
                    exclude_list = [u.strip().lower() for u in config.exclude_list.split(",") if u.strip()]
                    
                    for u in users:
                        uname_lower = u.username.lower()
                        if uname_lower not in all_users:
                            all_users[uname_lower] = {
                                "username": u.username,
                                "servers": {},
                                "excluded_from": []
                            }
                        all_users[uname_lower]["servers"][server_type.value] = {
                            "id": u.id,
                            "is_admin": u.is_admin
                        }
                        if uname_lower in exclude_list and server_type.value not in all_users[uname_lower]["excluded_from"]:
                            all_users[uname_lower]["excluded_from"].append(server_type.value)
                            
                for server_type, (client, config) in servers.items():
                    exclude_list = [u.strip().lower() for u in config.exclude_list.split(",") if u.strip()]
                    for exc_u in exclude_list:
                        if exc_u in all_users and server_type.value not in all_users[exc_u]["excluded_from"]:
                            all_users[exc_u]["excluded_from"].append(server_type.value)
                            
                return list(all_users.values())
            finally:
                await client_manager.close_all()
        except Exception as e:
            logger.error(f"Error getting all users: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/users/{server_name}/{username}")
    async def delete_user_from_server(server_name: str, username: str):
        """Delete a user from a specific server."""
        try:
            server_type = ServerType(server_name)
            config = config_service.get_server_config(server_name)
            if not config or not config.enabled:
                raise HTTPException(status_code=400, detail="Server not enabled")
                
            client_manager = APIClientManager()
            client = client_manager.get_or_create_client(server_type, config)
            if not client:
                raise HTTPException(status_code=400, detail="Could not create client")
                
            try:
                users = await client.get_users()
                user = next((u for u in users if u.username.lower() == username.lower()), None)
                if not user:
                    raise HTTPException(status_code=404, detail="User not found on server")
                    
                success, msg = await client.delete_user(user.id)
                if not success:
                    raise HTTPException(status_code=500, detail=msg)
                return {"success": True, "message": msg}
            finally:
                await client_manager.close_all()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting user {username} from {server_name}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.put("/api/users/{server_name}/exclude/{username}")
    async def toggle_user_exclude(server_name: str, username: str, req: Dict):
        """Toggle user exclusion on a specific server."""
        try:
            exclude = req.get("exclude", True)
            config = config_service.get_server_config(server_name)
            if not config:
                raise HTTPException(status_code=404, detail="Server not found")
                
            exclude_list = [u.strip().lower() for u in config.exclude_list.split(",") if u.strip()]
            uname_lower = username.lower()
            
            if exclude and uname_lower not in exclude_list:
                exclude_list.append(uname_lower)
            elif not exclude and uname_lower in exclude_list:
                exclude_list.remove(uname_lower)
                
            config.exclude_list = ", ".join(exclude_list)
            config_service.update_server_config(server_name, config)
            return {"success": True, "exclude_list": config.exclude_list}
        except Exception as e:
            logger.error(f"Error toggling exclude for {username} on {server_name}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/users/{username}/password")
    async def admin_change_password(username: str, req: Dict):
        """Admin force change user password across all servers."""
        try:
            new_password = req.get("password")
            if not new_password:
                raise HTTPException(status_code=400, detail="Password is required")
                
            client_manager = APIClientManager()
            successes = []
            errors = []
            
            for server_type in ServerType:
                config = config_service.get_server_config(server_type.value)
                if config and config.enabled:
                    client = client_manager.get_or_create_client(server_type, config)
                    if client:
                        users = await client.get_users()
                        user = next((u for u in users if u.username.lower() == username.lower()), None)
                        if user:
                            success, msg = await client.change_password(user.id, new_password)
                            if success:
                                successes.append(server_type.value)
                            else:
                                errors.append(f"{server_type.value}: {msg}")
            
            await client_manager.close_all()
            
            if not successes and not errors:
                raise HTTPException(status_code=404, detail="User not found on any active server")
                
            return {
                "success": len(errors) == 0,
                "message": f"Updated on {len(successes)} servers. Errors: {len(errors)}",
                "updated_servers": successes,
                "errors": errors
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error changing password for {username}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/users/{username}/reset-token")
    async def generate_reset_token(username: str):
        """Generate a password reset token for a user."""
        try:
            token_service = get_token_service()
            token = token_service.generate_reset_token(username)
            return {"success": True, "token": token}
        except Exception as e:
            logger.error(f"Error generating token for {username}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/reset-password")
    async def reset_password(req: Dict):
        """Public endpoint to reset password using a token."""
        try:
            token = req.get("token")
            new_password = req.get("password")
            
            if not token or not new_password:
                raise HTTPException(status_code=400, detail="Token and password are required")
                
            token_service = get_token_service()
            username = token_service.validate_token(token)
            
            if not username:
                raise HTTPException(status_code=400, detail="Invalid or expired token")
                
            # Change password on all servers
            client_manager = APIClientManager()
            successes = []
            
            for server_type in ServerType:
                config = config_service.get_server_config(server_type.value)
                if config and config.enabled:
                    client = client_manager.get_or_create_client(server_type, config)
                    if client:
                        users = await client.get_users()
                        user = next((u for u in users if u.username.lower() == username.lower()), None)
                        if user:
                            success, msg = await client.change_password(user.id, new_password)
                            if success:
                                successes.append(server_type.value)
            
            await client_manager.close_all()
            
            if successes:
                # Only consume token if we successfully changed it somewhere
                token_service.consume_token(token)
                return {"success": True, "message": "Password updated successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to update password on any server")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error resetting password: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/register")
    async def register_user(req: Dict):
        """Public endpoint to register a new user across all servers."""
        try:
            username = req.get("username")
            password = req.get("password")
            
            if not username or not password:
                raise HTTPException(status_code=400, detail="Username and password are required")
                
            username = username.strip()
            
            client_manager = APIClientManager()
            successes = []
            errors = []
            
            sync_config = config_service.get_sync_config()
            
            for server_type in ServerType:
                config = config_service.get_server_config(server_type.value)
                if config and config.enabled:
                    client = client_manager.get_or_create_client(server_type, config)
                    if client:
                        # Check if user already exists
                        users = await client.get_users()
                        user = next((u for u in users if u.username.lower() == username.lower()), None)
                        if user:
                            # User exists, skip creation for this server
                            continue
                            
                        success, user_id, error = await client.create_user(username, password)
                        if success:
                            successes.append(server_type.value)
                            # Apply template if available
                            if config.template_user:
                                template_data = await client.get_user_template(config.template_user)
                                if template_data and user_id:
                                    await client.update_user_from_template(user_id, template_data)
                        else:
                            errors.append(f"{server_type.value}: {error}")
                            
            await client_manager.close_all()
            
            if successes:
                return {"success": True, "message": f"Account created successfully on {len(successes)} servers"}
            elif errors:
                raise HTTPException(status_code=500, detail="Failed to create account: " + ", ".join(errors))
            else:
                return {"success": True, "message": "Username already exists"}
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error registering user: {str(e)}")
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

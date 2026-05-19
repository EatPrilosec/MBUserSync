"""Scheduled sync tasks."""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.config import get_config_service
from backend.services.sync_engine import get_sync_engine
from backend.clients import APIClientManager
from backend.models.schemas import ServerType

logger = logging.getLogger(__name__)


async def sync_task():
    """Scheduled sync task that runs based on cron schedule."""
    config_service = get_config_service()
    sync_engine = get_sync_engine()
    
    # Check if sync is enabled
    sync_config = config_service.get_sync_config()
    if not sync_config.sync_enabled:
        logger.debug("Sync disabled, skipping scheduled task")
        return
    
    if sync_engine.is_syncing:
        logger.warning("Sync already in progress, skipping this run")
        return
    
    logger.info(f"Starting scheduled sync (mode: {sync_config.sync_mode})")
    
    try:
        # Create client manager and build servers dict
        client_manager = APIClientManager()
        servers = {}
        
        for server_type in ServerType:
            config = config_service.get_server_config(server_type.value)
            if config and config.enabled:
                client = client_manager.get_or_create_client(server_type, config)
                if client:
                    servers[server_type] = (client, config)
        
        if not servers:
            logger.warning("No enabled servers, skipping sync")
            return
        
        # Run sync based on mode
        if sync_config.sync_mode.value == "primary_source":
            result = await sync_engine.sync_primary_source(servers)
        else:  # any_to_any
            result = await sync_engine.sync_any_to_any(servers)
        
        if result.success:
            logger.info(f"Sync completed successfully: {result.message}")
        else:
            logger.error(f"Sync completed with errors: {result.message}")
            for error in result.errors:
                logger.error(f"  - {error}")
        
    except Exception as e:
        logger.exception(f"Sync task failed: {str(e)}")
    finally:
        # Clean up clients
        try:
            await client_manager.close_all()
        except:
            pass


def setup_scheduler(scheduler: AsyncIOScheduler) -> None:
    """Set up scheduler jobs."""
    config_service = get_config_service()
    sync_config = config_service.get_sync_config()
    
    try:
        # Parse cron schedule
        cron_trigger = CronTrigger.from_crontab(sync_config.cron_schedule)
        
        scheduler.add_job(
            sync_task,
            trigger=cron_trigger,
            id="user_sync_job",
            name="User Sync Job",
            replace_existing=True,
            misfire_grace_time=60
        )
        
        logger.info(f"Scheduler set up with cron: {sync_config.cron_schedule}")
    except Exception as e:
        logger.error(f"Failed to set up scheduler: {str(e)}")

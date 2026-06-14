"""Main FastAPI application."""
import logging
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.config import get_config_service
from backend.scheduler.tasks import setup_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global scheduler
scheduler: AsyncIOScheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown."""
    global scheduler
    
    # Startup
    logger.info("Starting up application...")
    
    config_service = get_config_service()
    is_valid, errors = config_service.validate_config()
    
    if not is_valid:
        logger.warning(f"Configuration validation errors: {errors}")
    else:
        logger.info("Configuration validation passed")
    
    # Set up scheduler
    scheduler = AsyncIOScheduler()
    setup_scheduler(scheduler)
    scheduler.start()
    logger.info("Scheduler started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    if scheduler:
        scheduler.shutdown()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="MB User Sync",
    description="Synchronize users between media servers",
    version="1.0.0",
    lifespan=lifespan
)


# Import and include API routes
from backend.api import routes
routes.setup_routes(app)


# Serve React frontend
frontend_dist_path = Path(__file__).parent.parent / "frontend" / "dist"

from fastapi.responses import FileResponse

@app.get("/register", include_in_schema=False)
@app.get("/reset", include_in_schema=False)
async def serve_react_routes():
    """Serve the React index.html for specific client-side routes."""
    index_path = frontend_dist_path / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"detail": "Frontend not built"}

if frontend_dist_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist_path), html=True), name="static")
    logger.info(f"Mounted frontend from {frontend_dist_path}")
else:
    logger.warning(f"Frontend dist directory not found at {frontend_dist_path}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8670)

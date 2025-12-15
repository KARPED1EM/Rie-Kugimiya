import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.infrastructure.network.port_manager import PortManager
from src.infrastructure.utils.logger import (
    configure_unified_logging,
    get_uvicorn_log_config,
)
from src.core.config import app_config, websocket_config

logger = logging.getLogger(__name__)

configure_unified_logging()

PortManager.initialize(start_port=websocket_config.port, host=websocket_config.host)
port_manager = PortManager.get_instance()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: startup and shutdown events"""
    # Startup
    logger.info("Application starting up...")
    yield
    # Shutdown
    logger.info("Application shutting down...")
    try:
        # Import here to avoid circular dependencies
        from src.api.ws_routes import cleanup_resources
        await cleanup_resources()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown cleanup: {e}", exc_info=True)


app = FastAPI(title=app_config.app_name, debug=app_config.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=app_config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from src.api.ws_routes import router as ws_router
from src.api.ws_global_routes import router as ws_global_router
from src.api.routes import router as api_router

app.include_router(ws_router, prefix="/api")
app.include_router(ws_global_router, prefix="/api")
app.include_router(api_router, prefix="/api")

frontend_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../frontend")
)
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

else:
    logger.warning(f"Frontend directory not found at {frontend_dir}")


if __name__ == "__main__":
    import uvicorn

    port = port_manager.get_port()
    host = port_manager.get_host()

    logger.info(f"Starting server at {port_manager.get_base_url()}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        ws_ping_interval=websocket_config.ping_interval,
        ws_ping_timeout=websocket_config.ping_timeout,
        log_config=get_uvicorn_log_config(),
    )

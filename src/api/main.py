# FastAPI main application
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import logging
from .ws_routes import router as ws_router
from ..config import app_config, websocket_config

logger = logging.getLogger(__name__)

app = FastAPI(title=app_config.app_name, debug=app_config.debug)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket routes
app.include_router(ws_router, prefix="/api")

# Serve frontend
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_dir, "index.html"))
else:
    logger.warning(f"Frontend directory not found at {frontend_dir}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=websocket_config.host,
        port=websocket_config.port,
        ws_ping_interval=websocket_config.ping_interval,
        ws_ping_timeout=websocket_config.ping_timeout
    )
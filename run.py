"""
Quick start script for Yuzuriha Rin virtual character system
"""

import sys
import os
import io
import warnings

# Suppress jieba pkg_resources deprecation warning
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message=".*pkg_resources is deprecated.*",
    module="jieba._compat",
)

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    import uvicorn
    from src.infrastructure.network.port_manager import PortManager
    from src.api.main import app
    from src.core.utils.logger import get_uvicorn_log_config

    PortManager.initialize(start_port=8000, host="0.0.0.0")
    port_manager = PortManager.get_instance()

    port = port_manager.get_port()
    host = port_manager.get_host()

    print("=" * 60, flush=True)
    print("💕 Yuzuriha Rin 🌠", flush=True)
    print("=" * 60, flush=True)
    print("\nStarting server...", flush=True)
    print(f"  ✓ URL: {port_manager.get_base_url()}", flush=True)
    print(f"  ✓ Port: {port}", flush=True)
    print("\nPress Ctrl+C to stop\n", flush=True)
    print("=" * 60, flush=True)

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        ws_ping_interval=20.0,
        ws_ping_timeout=10.0,
        log_config=get_uvicorn_log_config(),
    )

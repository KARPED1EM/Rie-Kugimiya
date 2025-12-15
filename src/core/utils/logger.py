"""
Unified logging system with WebSocket support
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
import asyncio

try:
    from uvicorn.config import LOGGING_CONFIG as UVICORN_LOGGING_CONFIG
except Exception:
    UVICORN_LOGGING_CONFIG = None


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogCategory(str, Enum):
    SYSTEM = "system"
    BEHAVIOR = "behavior"
    EMOTION = "emotion"
    LLM = "llm"
    WEBSOCKET = "websocket"
    MESSAGE = "message"


class UnifiedLogger:
    """
    Unified logging system that supports both standard logging and WebSocket broadcasting
    """

    def __init__(self, name: str = "yuzuriha-rin"):
        self.logger = logging.getLogger(name)
        self.ws_manager = None
        self.debug_mode_enabled = False
        self._log_buffer: List[Dict[str, Any]] = []
        self._max_buffer_size = 1000

    def set_ws_manager(self, ws_manager):
        """Set WebSocket manager for broadcasting logs"""
        self.ws_manager = ws_manager

    def enable_debug_mode(self, enabled: bool = True):
        """Enable or disable debug mode (WebSocket log broadcasting)"""
        self.debug_mode_enabled = enabled

    def _format_log_entry(
        self,
        level: LogLevel,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Format log entry for storage and transmission"""
        return {
            "timestamp": datetime.now().timestamp(),
            "level": level.value,
            "category": category.value,
            "message": message,
            "metadata": metadata or {},
        }

    def _add_to_buffer(self, log_entry: Dict[str, Any]):
        """Add log entry to buffer with size limit"""
        self._log_buffer.append(log_entry)
        if len(self._log_buffer) > self._max_buffer_size:
            self._log_buffer.pop(0)

    async def _broadcast_log(self, log_entry: Dict[str, Any]):
        """Broadcast log to all connected debug clients"""
        if not self.debug_mode_enabled or not self.ws_manager:
            return

        try:
            # Broadcast to global debug connections
            await self.ws_manager.broadcast_global_debug_log(log_entry)
        except Exception as e:
            # Don't let logging errors break the application
            self.logger.error(f"Failed to broadcast log: {e}")

    def _log(
        self,
        level: LogLevel,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        metadata: Optional[Dict[str, Any]] = None,
        broadcast: bool = True,
    ):
        """Internal logging method"""
        # Standard logging
        log_func = getattr(self.logger, level.value)
        extra_info = f" [{category.value}]" if category != LogCategory.SYSTEM else ""
        log_func(f"{message}{extra_info}")

        # Format and store
        log_entry = self._format_log_entry(level, message, category, metadata)
        self._add_to_buffer(log_entry)

        # Async broadcast (will be handled by the caller if in async context)
        if broadcast and self.debug_mode_enabled:
            return log_entry
        return None

    def debug(
        self,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log debug message"""
        return self._log(LogLevel.DEBUG, message, category, metadata)

    def info(
        self,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log info message"""
        return self._log(LogLevel.INFO, message, category, metadata)

    def warning(
        self,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log warning message"""
        return self._log(LogLevel.WARNING, message, category, metadata)

    def error(
        self,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log error message"""
        return self._log(LogLevel.ERROR, message, category, metadata)

    def critical(
        self,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log critical message"""
        return self._log(LogLevel.CRITICAL, message, category, metadata)

    def behavior(self, action: str, details: Optional[Dict[str, Any]] = None):
        """Log behavior sequence"""
        message = f"Behavior action: {action}"
        return self._log(
            LogLevel.INFO,
            message,
            category=LogCategory.BEHAVIOR,
            metadata={"action": action, "details": details},
        )

    def emotion(self, emotion_map: Dict[str, str], context: Optional[str] = None):
        """Log emotion data"""
        emotions_str = ", ".join([f"{k}={v}" for k, v in emotion_map.items()])
        message = f"Emotion state: {emotions_str}"
        return self._log(
            LogLevel.INFO,
            message,
            category=LogCategory.EMOTION,
            metadata={"emotion_map": emotion_map, "context": context},
        )

    def llm_request(
        self,
        provider: str,
        model: str,
        messages: List[Dict[str, str]],
        token_count: Optional[int] = None,
    ):
        """Log LLM request with full context"""
        message = f"LLM request to {provider}/{model}"
        if token_count:
            message += f" ({token_count} tokens)"

        # Format messages for readability
        formatted_messages = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            formatted_messages.append(f"[{role}] {content[:100]}...")

        return self._log(
            LogLevel.INFO,
            message,
            category=LogCategory.LLM,
            metadata={
                "provider": provider,
                "model": model,
                "messages": messages,
                "token_count": token_count,
                "preview": formatted_messages,
            },
        )

    def llm_response(
        self,
        provider: str,
        model: str,
        response: str,
        emotion_map: Optional[Dict[str, str]] = None,
        token_count: Optional[int] = None,
    ):
        """Log LLM response"""
        message = f"LLM response from {provider}/{model}"
        if token_count:
            message += f" ({token_count} tokens)"

        return self._log(
            LogLevel.INFO,
            message,
            category=LogCategory.LLM,
            metadata={
                "provider": provider,
                "model": model,
                "response": response,
                "emotion_map": emotion_map,
                "token_count": token_count,
            },
        )

    def get_recent_logs(self, count: int = 100) -> List[Dict[str, Any]]:
        """Get recent logs from buffer"""
        return self._log_buffer[-count:]

    def clear_buffer(self):
        """Clear log buffer"""
        self._log_buffer.clear()


# Global logger instance
unified_logger = UnifiedLogger()


# Async wrapper for broadcasting logs
async def broadcast_log_if_needed(log_entry: Optional[Dict[str, Any]]):
    """Helper to broadcast log entry if it was returned from logging call"""
    if log_entry and unified_logger.debug_mode_enabled:
        await unified_logger._broadcast_log(log_entry)


class UnifiedLogHandler(logging.Handler):
    """
    Logging handler that forwards any standard logging record into unified_logger,
    so all logs can be displayed in the frontend debug panel.
    """

    def emit(self, record: logging.LogRecord):
        try:
            # Prevent feedback loops from unified_logger itself
            if record.name == unified_logger.logger.name:
                return

            level_name = record.levelname.lower()
            try:
                level = LogLevel(level_name)
            except Exception:
                level = LogLevel.INFO

            message = record.getMessage()
            category = getattr(record, "category", LogCategory.SYSTEM)
            if isinstance(category, str):
                try:
                    category = LogCategory(category)
                except Exception:
                    category = LogCategory.SYSTEM

            metadata = {
                "logger": record.name,
            }
            if record.exc_info:
                metadata["exc_info"] = True

            entry = unified_logger._format_log_entry(
                level=level, message=message, category=category, metadata=metadata
            )
            unified_logger._add_to_buffer(entry)

            if unified_logger.debug_mode_enabled and unified_logger.ws_manager:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(unified_logger._broadcast_log(entry))
                except Exception:
                    # No running loop; skip broadcast
                    pass
        except Exception:
            # Never raise from logging handler
            return


def configure_unified_logging():
    """
    Attach UnifiedLogHandler to root so non-unified loggers are still captured.
    Safe to call multiple times.
    """
    root = logging.getLogger()
    for h in root.handlers:
        if isinstance(h, UnifiedLogHandler):
            return
    root.addHandler(UnifiedLogHandler(level=logging.INFO))


def get_uvicorn_log_config():
    """
    Return a uvicorn log_config that uses the same level-prefixed format
    for all loggers (including project loggers).
    """
    if not UVICORN_LOGGING_CONFIG:
        return None

    config = dict(UVICORN_LOGGING_CONFIG)
    formatters = dict(config.get("formatters", {}))

    # Ensure the default formatter includes level prefix
    default_fmt = formatters.get("default", {})
    default_fmt = dict(default_fmt)
    default_fmt.setdefault("()", "uvicorn.logging.DefaultFormatter")
    default_fmt["fmt"] = "%(levelprefix)s %(message)s"
    formatters["default"] = default_fmt

    access_fmt = formatters.get("access", {})
    access_fmt = dict(access_fmt)
    access_fmt.setdefault("()", "uvicorn.logging.AccessFormatter")
    access_fmt["fmt"] = '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s'
    formatters["access"] = access_fmt

    config["formatters"] = formatters
    config["disable_existing_loggers"] = False
    return config

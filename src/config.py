# Backward compatibility - import from new location
from src.core.config import *

__all__ = [
    'AppConfig',
    'CharacterConfig', 
    'LLMDefaults',
    'UIDefaults',
    'WebSocketConfig',
    'DatabaseConfig',
    'app_config',
    'character_config',
    'llm_defaults',
    'ui_defaults',
    'websocket_config',
    'database_config',
]

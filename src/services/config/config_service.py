import logging
from typing import Dict, Optional
from src.infrastructure.database.repositories.config_repo import ConfigRepository
from src.core.config import llm_defaults, ui_defaults, app_config

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    # Protocol-based LLM configuration
    "llm_protocol": llm_defaults.protocol,
    "llm_base_url": llm_defaults.base_url,
    "llm_api_key": llm_defaults.api_key,
    "llm_model": llm_defaults.model,
    "llm_temperature": "",  # Optional, empty by default (don't send when empty)
    "llm_max_tokens": str(llm_defaults.max_tokens),
    # Default user nickname used in prompts if not set in UI.
    "user_nickname": "鲨鲨",
    "enable_emotion_theme": str(ui_defaults.enable_emotion_theme).lower(),
    "enable_debug_mode": "false",
}


class ConfigService:
    def __init__(self, config_repo: ConfigRepository):
        self.config_repo = config_repo

    async def get_config(self, key: str) -> Optional[str]:
        value = await self.config_repo.get_config(key)
        if value is None:
            return DEFAULT_CONFIG.get(key)
        return value

    async def get_all_config(self) -> Dict[str, str]:
        config = await self.config_repo.get_all_config()
        result = DEFAULT_CONFIG.copy()
        result.update(config)
        return result

    async def set_config(self, config: Dict[str, str]) -> bool:
        return await self.config_repo.set_config_batch(config)

    async def get_user_avatar(self, user_id: str) -> Optional[str]:
        return await self.config_repo.get_user_avatar(user_id)

    async def set_user_avatar(self, avatar_data: str, user_id: str) -> bool:
        return await self.config_repo.set_user_avatar(avatar_data, user_id)

    async def delete_user_avatar(self, user_id: str) -> bool:
        return await self.config_repo.delete_user_avatar(user_id)

    async def compute_hash(self) -> str:
        try:
            app_hash = await self.config_repo.compute_hash("app_config")
            user_hash = await self.config_repo.compute_hash("user_settings")
            char_hash = await self.config_repo.compute_hash("characters")
            session_hash = await self.config_repo.compute_hash("sessions")

            combined = f"{app_hash}{user_hash}{char_hash}{session_hash}"
            import hashlib

            return hashlib.sha256(combined.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error computing hash: {e}", exc_info=True)
            return ""

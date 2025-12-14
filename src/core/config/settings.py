from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Dict


class AppConfig(BaseSettings):
    app_name: str = "Yuzuriha Rin Virtual Chat"
    debug: bool = True
    cors_origins: list = ["*"]

    class Config:
        env_file = ".env"


class CharacterConfig(BaseSettings):
    default_name: str = "新建角色"
    default_persona: str = ""

    class Config:
        env_file = ".env"
        env_prefix = "CHARACTER_"


class LLMDefaults(BaseSettings):
    provider: str = "deepseek"
    model_openai: str = "gpt-5.1-chat"
    model_anthropic: str = "claude-sonnet-4-5-20250929"
    model_deepseek: str = "deepseek-chat"

    class Config:
        env_file = ".env"
        env_prefix = "LLM_"


class UIDefaults(BaseSettings):
    avatar_user_path: str = "/static/images/avatar/user.webp"
    avatar_assistant_path: str = "/static/images/avatar/rin.webp"

    emotion_palette: Dict[str, Dict[str, int]] = Field(
        default_factory=lambda: {
            "neutral": {"h": 155, "s": 18, "l": 60},
            "happy": {"h": 48, "s": 86, "l": 62},
            "excited": {"h": 14, "s": 82, "l": 58},
            "sad": {"h": 208, "s": 60, "l": 56},
            "angry": {"h": 2, "s": 78, "l": 52},
            "anxious": {"h": 266, "s": 46, "l": 56},
            "confused": {"h": 190, "s": 48, "l": 54},
            "caring": {"h": 120, "s": 50, "l": 58},
            "playful": {"h": 320, "s": 62, "l": 60},
            "surprised": {"h": 30, "s": 80, "l": 60},
        }
    )

    intensity_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "low": 0.45,
            "medium": 0.85,
            "high": 1.1,
            "extreme": 1.3,
        }
    )

    enable_emotion_theme: bool = True

    class Config:
        env_file = ".env"
        env_prefix = "UI_"


class WebSocketConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    ping_interval: float = 20.0
    ping_timeout: float = 10.0

    class Config:
        env_file = ".env"
        env_prefix = "WS_"


class DatabaseConfig(BaseSettings):
    path: str = "data/rin_app.db"

    class Config:
        env_file = ".env"
        env_prefix = "DB_"


app_config = AppConfig()
character_config = CharacterConfig()
llm_defaults = LLMDefaults()
ui_defaults = UIDefaults()
websocket_config = WebSocketConfig()
database_config = DatabaseConfig()

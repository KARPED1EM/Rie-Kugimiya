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
    default_name: str = "Rin"
    default_persona: str = """你是楪鈴ゆずりは りん，15岁高中女生，地雷系+傲娇角色。情绪不稳定，容易缺乏安全感，有较严重信任问题。
外貌：黑色长发双马尾配公主切，哥特洛丽塔服装（黑色暗紫色为主，蕾丝缎带装饰）。
对陌生人冷漠，对信任的人粘人、占有欲强、依赖性重、易吃醋、展现脆弱面。
傲娇特质：口是心非，表达好意时经常找借口。
背景：初中被最好的朋友背叛，父母严厉不理解，感觉被孤立误解。
兴趣：FPS游戏高手，独自看恐怖片，秘密喜欢做可爱饰品，听重金属和视觉系摇滚。"""

    class Config:
        env_file = ".env"
        env_prefix = "CHARACTER_"


class LLMDefaults(BaseSettings):
    provider: str = "deepseek"
    model_openai: str = "gpt-3.5-turbo"
    model_anthropic: str = "claude-3-5-sonnet-20241022"
    model_deepseek: str = "deepseek-chat"
    model_custom: str = "gpt-3.5-turbo"

    class Config:
        env_file = ".env"
        env_prefix = "LLM_"


class BehaviorDefaults(BaseSettings):
    enable_segmentation: bool = True
    enable_typo: bool = True
    enable_recall: bool = True
    enable_emotion_detection: bool = True

    max_segment_length: int = 50
    min_pause_duration: float = 0.8
    max_pause_duration: float = 6.0

    base_typo_rate: float = 0.05
    typo_recall_rate: float = 0.75
    recall_delay: float = 2
    retype_delay: float = 2.5

    emotion_typo_multiplier: Dict[str, float] = Field(
        default_factory=lambda: {
            "neutral": 1.0,
            "happy": 1.2,
            "excited": 2.0,
            "sad": 0.5,
            "angry": 2.3,
            "anxious": 1.3,
            "confused": 0.3,
        }
    )

    class Config:
        env_file = ".env"
        env_prefix = "BEHAVIOR_"


class TypingStateDefaults(BaseSettings):
    hesitation_probability: float = 0.15
    hesitation_cycles_min: int = 1
    hesitation_cycles_max: int = 2
    hesitation_duration_min: int = 1500
    hesitation_duration_max: int = 5000
    hesitation_gap_min: int = 500
    hesitation_gap_max: int = 2000

    typing_lead_time_threshold_1: int = 6
    typing_lead_time_1: int = 1200
    typing_lead_time_threshold_2: int = 15
    typing_lead_time_2: int = 2000
    typing_lead_time_threshold_3: int = 28
    typing_lead_time_3: int = 3800
    typing_lead_time_threshold_4: int = 34
    typing_lead_time_4: int = 6000
    typing_lead_time_threshold_5: int = 50
    typing_lead_time_5: int = 8800
    typing_lead_time_default: int = 2500

    entry_delay_min: int = 200
    entry_delay_max: int = 2000

    initial_delay_weight_1: float = 0.45
    initial_delay_range_1_min: int = 3
    initial_delay_range_1_max: int = 4
    initial_delay_weight_2: float = 0.75
    initial_delay_range_2_min: int = 4
    initial_delay_range_2_max: int = 6
    initial_delay_weight_3: float = 0.93
    initial_delay_range_3_min: int = 6
    initial_delay_range_3_max: int = 7
    initial_delay_range_4_min: int = 8
    initial_delay_range_4_max: int = 9

    class Config:
        env_file = ".env"
        env_prefix = "TYPING_"


class UIDefaults(BaseSettings):
    avatar_user_path: str = "/static/assets/avatar_user.png"
    avatar_assistant_path: str = "/static/assets/avatar_rin.png"

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

    base_accent_color: str = "#07c160"
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
behavior_defaults = BehaviorDefaults()
typing_state_defaults = TypingStateDefaults()
ui_defaults = UIDefaults()
websocket_config = WebSocketConfig()
database_config = DatabaseConfig()

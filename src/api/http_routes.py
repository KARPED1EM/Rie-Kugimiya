import logging
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, get_args, get_origin
from pydantic_core import PydanticUndefined
from src.infrastructure.database.connection import DatabaseConnection
from src.services.character.character_service import CharacterService
from src.services.configurations.config_service import ConfigService
from src.services.messaging.message_service import MessageService
from src.infrastructure.database.repositories import (
    MessageRepository,
    CharacterRepository,
    SessionRepository,
    ConfigRepository,
)
from src.core.configs import database_config
from src.core.models.constants import DEFAULT_USER_ID
from src.core.models.character import Character
from src.utils.url_utils import sanitize_base_url
from src.core.utils.logger import (
    unified_logger,
    broadcast_log_if_needed,
    LogCategory,
)

logger = logging.getLogger(__name__)

router = APIRouter()

STICKER_BASE_DIR = Path(__file__).parent.parent.parent / "assets" / "stickers"

# Character fields that should not be updated via behavior_params
PROTECTED_CHARACTER_FIELDS = {
    "behavior", "id", "name", "avatar", "persona", 
    "is_builtin", "created_at", "updated_at"
}

# Service instances
db_connection: Optional[DatabaseConnection] = None
character_service: Optional[CharacterService] = None
config_service: Optional[ConfigService] = None
message_service: Optional[MessageService] = None
session_repo: Optional[SessionRepository] = None



async def initialize_services():
    global db_connection, character_service, config_service, message_service, session_repo

    if db_connection is None:
        try:
            db_connection = DatabaseConnection(database_config.path)

            # Create repositories
            message_repo = MessageRepository(db_connection)
            character_repo = CharacterRepository(db_connection)
            session_repo = SessionRepository(db_connection)
            config_repo = ConfigRepository(db_connection)

            # Create services
            message_service = MessageService(message_repo)
            config_service = ConfigService(config_repo)
            character_service = CharacterService(
                character_repo, session_repo, message_service, config_service
            )

            await character_service.initialize_builtin_characters()
            logger.info("REST API services initialized")
        except Exception as e:
            logger.error(f"Error initializing services: {e}", exc_info=True)
            # Reset to None to force retry
            db_connection = None
            character_service = None
            config_service = None
            message_service = None
            session_repo = None
            raise


class CharacterCreate(BaseModel):
    name: str
    avatar: Optional[str] = None
    persona: Optional[str] = None
    sticker_packs: Optional[List[str]] = None
    behavior_params: Optional[Dict[str, Any]] = None


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    persona: Optional[str] = None
    sticker_packs: Optional[List[str]] = None
    behavior_params: Optional[Dict[str, Any]] = None


class ConfigUpdate(BaseModel):
    config: Dict[str, str]


class AvatarUpdate(BaseModel):
    avatar: Optional[str] = None


def _pydantic_field_default(field) -> Any:
    if field.default is not PydanticUndefined:
        return field.default
    if getattr(field, "default_factory", None):
        try:
            return field.default_factory()
        except Exception:
            return None
    return None


def _annotation_to_type_name(annotation: Any) -> str:
    origin = get_origin(annotation)
    if origin is None:
        try:
            return annotation.__name__
        except Exception:
            return str(annotation)

    if origin in (list, List):
        args = get_args(annotation)
        if args:
            return f"list[{_annotation_to_type_name(args[0])}]"
        return "list"

    if str(origin) == "typing.Union":
        args = [a for a in get_args(annotation) if a is not type(None)]  # noqa: E721
        if len(args) == 1:
            return _annotation_to_type_name(args[0])
        return "union"

    return str(origin)


def _normalize_string_list(values: Optional[List[str]]) -> List[str]:
    out: List[str] = []
    for item in list(values or []):
        s = str(item).strip()
        if not s:
            continue
        if s not in out:
            out.append(s)
    return out


_ALLOWED_LOCAL_AVATARS = {
    "/static/images/avatar/rin.webp",
    "/static/images/avatar/abai.webp",
    "/static/images/avatar/user.webp",
    "/static/images/avatar/default.webp",
}


def _validate_avatar_value(value: Optional[str], *, allow_local: bool) -> str:
    """
    Allowed avatar values (stored in DB):
    - "" (empty) -> use frontend fallback default
    - whitelisted local static path (allow_local=True only)
    - http(s) URL
    - data:image/* data URL
    """
    s = (value or "").strip()
    if not s:
        return ""

    lower = s.lower()
    if lower.startswith("data:image/"):
        return s

    if lower.startswith("http://") or lower.startswith("https://"):
        return s

    if allow_local and s in _ALLOWED_LOCAL_AVATARS:
        return s

    raise HTTPException(status_code=400, detail="Invalid avatar value")


@router.get("/characters/behavior-schema")
async def get_character_behavior_schema():
    """
    Return a machine-readable schema for all character behavior-system fields.
    Frontend uses this to render editable controls without duplicating field lists.
    Fields are automatically grouped by module name from the nested BehaviorConfig structure.
    """
    from src.core.models.behavior import BehaviorConfig

    fields: List[Dict[str, Any]] = []
    
    # Handle sticker_packs field separately (not part of nested behavior config)
    sticker_packs_field = Character.model_fields.get("sticker_packs")
    if sticker_packs_field:
        fields.append({
            "key": "sticker_packs",
            "type": _annotation_to_type_name(sticker_packs_field.annotation),
            "default": _pydantic_field_default(sticker_packs_field),
            "group": "sticker",
        })
    
    # Extract fields from nested BehaviorConfig structure
    # Note: BehaviorConfig() is lightweight - only creates config objects with defaults
    behavior_config = BehaviorConfig()
    for module_name, module_field in BehaviorConfig.model_fields.items():
        # Get the config class for this module (e.g., TimelineConfig, SegmenterConfig)
        module_config = getattr(behavior_config, module_name)
        module_config_class = type(module_config)
        
        # Iterate through fields in this module's config
        for field_name, field_info in module_config_class.model_fields.items():
            # Construct the flat field key (e.g., "timeline_hesitation_probability")
            flat_key = f"{module_name}_{field_name}"
            
            type_name = _annotation_to_type_name(field_info.annotation)
            default_value = _pydantic_field_default(field_info)
            
            fields.append({
                "key": flat_key,
                "type": type_name,
                "default": default_value,
                "group": module_name,
            })
    
    return {"fields": fields}


@router.get("/characters")
async def get_characters():
    await initialize_services()
    characters = await character_service.get_all_characters()
    return {"characters": [char.model_dump() for char in characters]}


@router.get("/characters/{character_id}")
async def get_character(character_id: str):
    await initialize_services()
    character = await character_service.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return {"character": character.model_dump()}


@router.post("/characters")
async def create_character(data: CharacterCreate):
    await initialize_services()

    character = await character_service.create_character(
        name=data.name,
        avatar=(
            _validate_avatar_value(data.avatar, allow_local=True)
            if data.avatar is not None
            else None
        ),
        persona=(data.persona or ""),
        sticker_packs=data.sticker_packs,
        behavior_params=data.behavior_params,
    )

    if not character:
        raise HTTPException(status_code=500, detail="Failed to create character")

    return {"character": character.model_dump()}


@router.put("/characters/{character_id}")
async def update_character(character_id: str, data: CharacterUpdate):
    await initialize_services()

    character = await character_service.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    if character.is_builtin:
        raise HTTPException(status_code=403, detail="Cannot modify builtin character")

    if data.name is not None:
        character.name = data.name
    if data.avatar is not None:
        character.avatar = _validate_avatar_value(data.avatar, allow_local=True)
    if data.persona is not None:
        character.persona = data.persona or ""
    if data.sticker_packs is not None:
        character.sticker_packs = _normalize_string_list(data.sticker_packs)
    if data.behavior_params:
        for key, value in data.behavior_params.items():
            try:
                # Handle nested behavior config fields (e.g., "timeline_hesitation_probability")
                if "_" in key:
                    parts = key.split("_", 1)
                    module_name = parts[0]
                    field_name = parts[1]
                    
                    # Check if this is a valid module in BehaviorConfig
                    if hasattr(character.behavior, module_name):
                        module_config = getattr(character.behavior, module_name)
                        if hasattr(module_config, field_name):
                            # Pydantic will validate the value type when setting
                            setattr(module_config, field_name, value)
                        else:
                            logger.warning(f"Unknown behavior field: {module_name}.{field_name}")
                # Handle top-level fields like sticker_packs (already handled above, but kept for completeness)
                elif hasattr(character, key) and key not in PROTECTED_CHARACTER_FIELDS:
                    setattr(character, key, value)
            except (ValueError, TypeError) as e:
                # Log validation errors but continue processing other fields
                logger.warning(f"Invalid value for {key}: {e}")

    success = await character_service.update_character(character)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update character")

    # Update character configuration in active SessionService instances
    from src.api import ws_routes

    updated_sessions = []
    for session_id, session_client in list(ws_routes.session_clients.items()):
        if (
            hasattr(session_client, "character")
            and session_client.character.id == character_id
        ):
            try:
                # Update the character configuration in the SessionService
                session_client.update_character(character)
                # Send notification to frontend that config is updated
                if ws_routes.ws_manager:
                    await ws_routes.ws_manager.send_toast(
                        session_id, "角色配置已更新", level="info"
                    )
                updated_sessions.append(session_id)
            except Exception as e:
                log_entry = unified_logger.warning(
                    f"Failed to update character for session {session_id}: {e}",
                    category=LogCategory.BEHAVIOR,
                )
                await broadcast_log_if_needed(log_entry)

    if updated_sessions:
        log_entry = unified_logger.info(
            f"Character config updated for {len(updated_sessions)} active sessions",
            category=LogCategory.BEHAVIOR,
            metadata={
                "character_id": character_id,
                "sessions": updated_sessions,
            },
        )
        await broadcast_log_if_needed(log_entry)

    return {"character": character.model_dump()}


@router.delete("/characters/{character_id}")
async def delete_character(character_id: str):
    await initialize_services()

    success = await character_service.delete_character(character_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete character")

    return {"success": True}


@router.get("/sessions")
async def get_sessions():
    await initialize_services()
    sessions = await session_repo.get_all()
    return {"sessions": [sess.model_dump() for sess in sessions]}


@router.get("/sessions/active")
async def get_active_session():
    await initialize_services()
    session = await session_repo.get_active_session()
    if not session:
        return {"session": None}
    return {"session": session.model_dump()}


@router.post("/sessions/{session_id}/activate")
async def activate_session(session_id: str):
    await initialize_services()

    success = await character_service.switch_active_session(session_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to activate session")

    return {"success": True}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, after: float = 0):
    """
    Incremental message sync over HTTP.
    Returns all messages with timestamp > after.
    """
    await initialize_services()
    messages = await message_service.get_messages(session_id, after)
    return {
        "messages": [
            {
                "id": msg.id,
                "session_id": msg.session_id,
                "sender_id": msg.sender_id,
                "type": msg.type,
                "content": msg.content,
                "metadata": msg.metadata,
                "is_recalled": msg.is_recalled,
                "is_read": msg.is_read,
                "timestamp": msg.timestamp,
            }
            for msg in messages
        ]
    }


@router.get("/config")
async def get_config():
    await initialize_services()
    config = await config_service.get_all_config()
    return {"config": config}


@router.post("/config")
async def update_config(data: ConfigUpdate):
    await initialize_services()
    config_updates = data.config.copy()
    if "llm_base_url" in config_updates:
        config_updates["llm_base_url"] = sanitize_base_url(
            config_updates.get("llm_base_url")
        )
    success = await config_service.set_config(config_updates)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update config")

    return {"success": True}


@router.get("/hash")
async def get_hash():
    await initialize_services()
    hash_value = await config_service.compute_hash()
    return {"hash": hash_value}


@router.get("/avatar")
async def get_user_avatar(user_id: str = DEFAULT_USER_ID):
    await initialize_services()
    avatar = await config_service.get_user_avatar(user_id)
    return {"avatar": avatar}


@router.post("/avatar")
async def upload_user_avatar(data: AvatarUpdate, user_id: str = DEFAULT_USER_ID):
    await initialize_services()

    avatar = _validate_avatar_value(data.avatar, allow_local=False)

    if not avatar:
        success = await config_service.delete_user_avatar(user_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete avatar")
        return {"success": True}

    success = await config_service.set_user_avatar(avatar, user_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to upload avatar")

    return {"success": True}


@router.delete("/avatar")
async def delete_user_avatar(user_id: str = DEFAULT_USER_ID):
    await initialize_services()

    success = await config_service.delete_user_avatar(user_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete avatar")

    return {"success": True}


@router.get("/stickers/{path:path}")
async def get_sticker(path: str):
    sticker_path = (STICKER_BASE_DIR / path).resolve()
    base_resolved = STICKER_BASE_DIR.resolve()

    try:
        sticker_path.relative_to(base_resolved)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if not sticker_path.exists() or not sticker_path.is_file():
        raise HTTPException(status_code=404, detail="Sticker not found")

    return FileResponse(sticker_path)

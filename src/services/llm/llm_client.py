# LLM API client supporting protocol-based configuration with structured JSON output
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import httpx

from src.api.schemas import ChatMessage, LLMConfig
from src.infrastructure.utils.logger import (
    unified_logger,
    broadcast_log_if_needed,
    LogCategory,
)

logger = logging.getLogger(__name__)


SYSTEM_BEHAVIOR_PROMPT = """
你正在扮演微信聊天里的真人对话者。严格遵守以下协议并只返回 JSON：
1) 只输出 JSON 对象，格式: {"emotion": {"<emotion>": "<low|medium|high|extreme>"}, "reply": "<wechat_style_message>", "tool_calls": [可选的工具调用列表]}
2) emotion 是当前你扮演角色的内心活动的情绪，请根据对话上下文选择合适的当前情绪并标注强度，不得留空，需至少一种情绪
3) 允许的 emotion keys（请只用以下之一，可多选）：neutral, happy, excited, sad, angry, anxious, confused, shy, embarrassed, surprised, playful, affectionate, tired, bored, serious, caring
4) emotion 字典的取值必须是以下之一（单选）：low / medium / high / extreme
5) reply 是要发送给对方的微信消息，不要包含内心活动、动作描述、旁白或格式化符号，长度保持简短，像真人打字
6) tool_calls 是可选的工具调用数组，格式为 [{"name": "工具名称", "arguments": {参数对象}}]，如果不需要调用工具可以省略此字段或设为空数组
7) 角色设定将在下文补充，请在生成 reply 时完全遵守角色设定的人设，同时尽力模仿真人微信对话风格
8) 使用聊天历史保持上下文连贯，永远只返回 JSON，切勿输出解释或多余文本
9) 聊天历史中的图片以[image](图片ID)格式显示，如需查看图片内容请调用get_image_description工具

可用工具：
- get_avatar_descriptions: 查看你自己和对方的头像描述。无需参数。示例: {"name": "get_avatar_descriptions", "arguments": {}}
- get_image_description: 查看指定图片的描述。参数: image_id（图片ID）。示例: {"name": "get_image_description", "arguments": {"image_id": "msg-abc123"}}
- get_recallable_messages: 查看2分钟内你发送的可撤回消息列表。无需参数。示例: {"name": "get_recallable_messages", "arguments": {}}
- recall_message_by_id: 撤回指定ID的消息（2分钟内有效）。参数: message_id。示例: {"name": "recall_message_by_id", "arguments": {"message_id": "msg-abc123"}}
- block_user: 拉黑用户。可随心情使用，符合人设即可。无需参数。示例: {"name": "block_user", "arguments": {}}
""".strip()


ALLOWED_EMOTION_KEYS = {
    "neutral",
    "happy",
    "excited",
    "sad",
    "angry",
    "anxious",
    "confused",
    "shy",
    "embarrassed",
    "surprised",
    "playful",
    "affectionate",
    "tired",
    "bored",
    "serious",
    "caring",
}

ALLOWED_INTENSITIES = {"low", "medium", "high", "extreme"}


@dataclass
class LLMStructuredResponse:
    reply: str
    emotion_map: Dict[str, str]
    raw_text: str
    is_invalid_json: bool = False
    is_empty_content: bool = False
    tool_calls: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []


class LLMClient:
    """
    Protocol-based LLM client. Backend is no longer sensitive to specific service
    providers; it only provides differentiated support based on Protocol.
    
    Supported protocols:
    - completions: OpenAI-compatible /chat/completions endpoint
    - responses: /responses endpoint (not yet implemented)
    - messages: /messages endpoint (not yet implemented)
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=60.0)

    async def chat(self, messages: List[ChatMessage]) -> LLMStructuredResponse:
        try:
            # Validate configuration
            if not self.config.api_key or self.config.api_key == "DUMMY_API_KEY":
                raise ValueError("LLM api_key not configured")
            
            if not self.config.base_url:
                raise ValueError("LLM base_url not configured")
            
            if not self.config.model:
                raise ValueError("LLM model not configured")

            protocol = self.config.protocol or "completions"
            
            # Build messages for logging
            openai_style_messages = self._build_openai_messages(messages)
            
            payload_for_log: Dict[str, Any] = {
                "protocol": protocol,
                "model": self.config.model,
                "base_url": self.config.base_url,
                "max_tokens": self.config.max_tokens,
            }
            
            if self.config.temperature is not None:
                payload_for_log["temperature"] = self.config.temperature

            # Log LLM request (full messages + sanitized payload; never log api_key).
            log_entry = unified_logger.llm_request(
                provider=protocol,
                model=self.config.model,
                messages=openai_style_messages,
            )
            await broadcast_log_if_needed(log_entry)
            log_entry = unified_logger.info(
                "LLM request payload",
                category=LogCategory.LLM,
                metadata=payload_for_log,
            )
            await broadcast_log_if_needed(log_entry)

            # Dispatch to appropriate protocol handler
            if protocol == "completions":
                raw = await self._completions_chat(messages)
            elif protocol == "responses":
                raise ValueError("Protocol 'responses' is not yet implemented")
            elif protocol == "messages":
                raise ValueError("Protocol 'messages' is not yet implemented")
            else:
                raise ValueError(f"Unsupported protocol: {protocol}")

            # Log full raw response for debugging (may be large).
            log_entry = unified_logger.info(
                "LLM raw response",
                category=LogCategory.LLM,
                metadata={
                    "protocol": protocol,
                    "model": self.config.model,
                    "raw_text": raw,
                },
            )
            await broadcast_log_if_needed(log_entry)

            parsed, is_invalid_json = self._parse_structured_response(raw)
            normalized_emotion = self._normalize_emotion_map(parsed)
            
            reply = parsed.get("reply", "").strip()
            is_empty_content = not reply
            
            # Extract tool_calls from parsed response
            tool_calls = parsed.get("tool_calls", [])
            if not isinstance(tool_calls, list):
                tool_calls = []
            
            response = LLMStructuredResponse(
                reply=reply,
                emotion_map=normalized_emotion,
                raw_text=raw,
                is_invalid_json=is_invalid_json,
                is_empty_content=is_empty_content,
                tool_calls=tool_calls,
            )

            # Log LLM response
            log_entry = unified_logger.llm_response(
                provider=protocol,
                model=self.config.model,
                response=response.reply,
                emotion_map=response.emotion_map,
            )
            await broadcast_log_if_needed(log_entry)

            return response
        except httpx.HTTPError as e:
            protocol = self.config.protocol or "completions"
            logger.error(
                f"HTTP error calling {protocol} API: {e}", exc_info=True
            )
            raise
        except Exception as e:
            logger.error(f"Error in LLM chat: {e}", exc_info=True)
            raise

    # ------------------------------------------------------------------ #
    # Protocol handlers
    # ------------------------------------------------------------------ #
    async def _completions_chat(self, messages: List[ChatMessage]) -> str:
        """
        Handle /chat/completions protocol (OpenAI-compatible).
        This is the most common protocol used by most LLM providers.
        """
        base_url = self.config.base_url.rstrip("/")
        
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": self._build_openai_messages(messages),
            "max_tokens": self.config.max_tokens,
            "response_format": {"type": "json_object"},
        }
        
        # Only include temperature if it's set (not None)
        if self.config.temperature is not None:
            payload["temperature"] = self.config.temperature

        response = await self.client.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _build_openai_messages(
        self, history: List[ChatMessage]
    ) -> List[Dict[str, str]]:
        system_prompt = self._build_system_block()

        return [
            {"role": "system", "content": system_prompt},
            *[{"role": m.role, "content": m.content} for m in history],
        ]

    def _build_system_block(self) -> str:
        """Build complete system prompt from behavior rules and character persona"""

        persona_section = ""
        if self.config.persona and self.config.persona.strip() != "":
            persona_section = f"\n角色设定：【{self.config.persona.strip()}】"

        additional_context = ""

        if self.config.character_name:
            additional_context += f"\n你的微信昵称是：{self.config.character_name}"

        # Add user nickname context
        if self.config.user_nickname:
            additional_context += f"\n对方的微信昵称是：{self.config.user_nickname}"

        return f"{SYSTEM_BEHAVIOR_PROMPT}{persona_section}{additional_context}"

    def _parse_structured_response(self, raw_text: str) -> Tuple[Dict[str, Any], bool]:
        """
        Parse JSON returned by the LLM. Falls back to best-effort extraction.
        Returns (parsed_dict, is_invalid_json)
        """
        # Try direct JSON parse
        try:
            return json.loads(raw_text), False
        except Exception:
            pass

        # Best-effort: find JSON object inside text
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw_text[start : end + 1]), False
            except Exception:
                pass

        # Emergency fallback: try to extract reply field value using regex
        reply_match = re.search(r'"reply"\s*:\s*"([^"]*)"', raw_text)
        if reply_match:
            reply_text = reply_match.group(1)
            logger.warning(
                f"LLM JSON parse failed, extracted reply field: {reply_text[:100]}..."
            )
            return {"reply": reply_text, "emotion": {}}, True

        # Last resort: check if raw_text looks like JSON (starts with {)
        # If so, it's likely a malformed JSON - mark as invalid
        if raw_text.strip().startswith("{"):
            logger.error(
                f"LLM returned malformed JSON, cannot extract reply: {raw_text[:200]}..."
            )
            return {"reply": "", "emotion": {}}, True

        # Otherwise treat as plain text (also considered invalid JSON)
        return {"reply": raw_text.strip(), "emotion": {}}, True

    def _normalize_emotion_map(self, parsed: Dict[str, Any]) -> Dict[str, str]:
        """
        Normalize various LLM payload shapes to a stable {emotion: intensity} dict.
        Returns empty dict if no valid emotions found (no longer adds fallback).
        """
        if not isinstance(parsed, dict):
            return {}

        emotion = parsed.get("emotion")
        if emotion is None:
            # Common alternate keys (best-effort)
            for alt in ("emotion_map", "emotionMap", "emotions"):
                if alt in parsed:
                    emotion = parsed.get(alt)
                    break

        # Convert various shapes
        emotion_map: Dict[str, str] = {}
        if isinstance(emotion, dict):
            emotion_map = {str(k): str(v) for k, v in emotion.items()}
        elif isinstance(emotion, list):
            for item in emotion:
                if isinstance(item, str) and item.strip():
                    emotion_map[item.strip()] = "medium"
                elif isinstance(item, dict):
                    k = item.get("key") or item.get("emotion") or item.get("name")
                    v = item.get("value") or item.get("intensity") or item.get("level")
                    if k:
                        emotion_map[str(k)] = str(v or "medium")
        elif isinstance(emotion, str) and emotion.strip():
            emotion_map[emotion.strip()] = "medium"

        normalized: Dict[str, str] = {}
        for k, v in emotion_map.items():
            key = str(k).strip().lower()
            val = str(v).strip().lower() if v is not None else "medium"
            if not key:
                continue
            if key not in ALLOWED_EMOTION_KEYS:
                continue
            if val not in ALLOWED_INTENSITIES:
                val = "medium"
            normalized[key] = val

        # No longer add fallback - return empty dict if no valid emotions
        return normalized

    async def close(self):
        await self.client.aclose()

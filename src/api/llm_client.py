# LLM API client supporting multiple providers with structured JSON output
import json
from dataclasses import dataclass
from typing import Any, Dict, List

import httpx

from .schemas import ChatMessage, LLMConfig


SYSTEM_BEHAVIOR_PROMPT = """
你正在扮演微信聊天里的真人对话者。严格遵守以下协议并只返回 JSON：
1) 只输出 JSON 对象，格式: {"emotion": {"<emotion>": "<low|medium|high|extreme>"}, "reply": "<wechat_style_message>"}
2) 允许的 emotion keys（请只用以下之一，可多选）：neutral, happy, excited, sad, angry, anxious, confused, shy, embarrassed, surprised, playful, affectionate, tired, bored, serious, caring
3) emotion 字典的取值必须是 low / medium / high / extreme
4) reply 是要发送给对方的微信消息，不要包含内心活动、旁白或格式化符号，长度保持简短，像真人打字
5) 角色设定将由系统补充，请在生成 reply 时完全遵守角色设定的人设，但前提是尽力模仿真人微信对话风格
6) 使用聊天历史保持上下文连贯，永远只返回 JSON，切勿输出解释或多余文本
""".strip()


@dataclass
class LLMStructuredResponse:
    reply: str
    emotion_map: Dict[str, str]
    raw_text: str


class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=60.0)

    async def chat(self, messages: List[ChatMessage], character_name: str = "Rin") -> LLMStructuredResponse:
        if self.config.provider == "openai":
            raw = await self._openai_chat(messages, character_name)
        elif self.config.provider == "anthropic":
            raw = await self._anthropic_chat(messages, character_name)
        elif self.config.provider == "deepseek":
            raw = await self._deepseek_chat(messages, character_name)
        elif self.config.provider == "custom":
            raw = await self._custom_chat(messages, character_name)
        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")

        parsed = self._parse_structured_response(raw)
        return LLMStructuredResponse(
            reply=parsed.get("reply", "").strip(),
            emotion_map=parsed.get("emotion", {}) or {},
            raw_text=raw,
        )

    # ------------------------------------------------------------------ #
    # Provider adapters
    # ------------------------------------------------------------------ #
    async def _openai_chat(self, messages: List[ChatMessage], character_name: str) -> str:
        base_url = self.config.base_url or "https://api.openai.com/v1"

        payload = {
            "model": self.config.model,
            "messages": self._build_openai_messages(messages, character_name),
            "response_format": {"type": "json_object"},
        }

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

    async def _anthropic_chat(self, messages: List[ChatMessage], character_name: str) -> str:
        base_url = self.config.base_url or "https://api.anthropic.com/v1"

        payload = {
            "model": self.config.model,
            "max_tokens": 1024,
            "system": self._build_system_block(character_name),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }

        response = await self.client.post(
            f"{base_url}/messages",
            json=payload,
            headers={
                "x-api-key": self.config.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]

    async def _deepseek_chat(self, messages: List[ChatMessage], character_name: str) -> str:
        base_url = self.config.base_url or "https://api.deepseek.com"

        payload = {
            "model": self.config.model,
            "messages": self._build_openai_messages(messages, character_name),
            "stream": False,
        }

        url = f"{base_url}/v1/chat/completions"

        response = await self.client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def _custom_chat(self, messages: List[ChatMessage], character_name: str) -> str:
        if not self.config.base_url:
            raise ValueError("base_url required for custom provider")

        payload = {
            "model": self.config.model,
            "messages": self._build_openai_messages(messages, character_name),
        }

        response = await self.client.post(
            f"{self.config.base_url}/chat/completions",
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
    def _build_openai_messages(self, history: List[ChatMessage], character_name: str) -> List[Dict[str, str]]:
        system_prompt = self._build_system_block(character_name)

        return [
            {"role": "system", "content": system_prompt},
            *[{"role": m.role, "content": m.content} for m in history],
        ]

    def _build_system_block(self, character_name: str) -> str:
        """Build complete system prompt from behavior rules and character persona"""
        char_name = character_name or "Rin"
        persona_section = ""
        if self.config.persona:
            persona_section = f"\n角色设定：{self.config.persona.strip()}"
        return f"{SYSTEM_BEHAVIOR_PROMPT}\n角色名：{char_name}{persona_section}"

    def _parse_structured_response(self, raw_text: str) -> Dict[str, Any]:
        """
        Parse JSON returned by the LLM. Falls back to best-effort extraction.
        """
        try:
            return json.loads(raw_text)
        except Exception:
            pass

        # Best-effort: find JSON object inside text
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw_text[start : end + 1])
            except Exception:
                return {"reply": raw_text.strip(), "emotion": {}}

        return {"reply": raw_text.strip(), "emotion": {}}

    async def close(self):
        await self.client.aclose()

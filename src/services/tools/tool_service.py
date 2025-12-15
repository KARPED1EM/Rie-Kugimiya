"""Tool service for LLM API tool calls."""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from src.core.models.message import Message, MessageType
from src.services.messaging.message_service import MessageService
from src.utils.image_alter import image_alter


# Tool definitions for LLM (can be customized in future)
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_avatar_descriptions",
            "description": "查看当前角色自己和用户的头像描述信息。不需要任何参数，直接调用即可获取双方的头像描述。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_image_description",
            "description": "查看指定图片的描述信息。当消息历史中出现[image](图片ID)时，可以调用此工具查看图片的详细描述。",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_id": {
                        "type": "string",
                        "description": "图片ID（即消息ID）",
                    }
                },
                "required": ["image_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recallable_messages",
            "description": "查看可撤回的消息列表。返回2分钟内所有由AI助手（assistant）发送的、尚未被撤回的消息及其ID。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_message_by_id",
            "description": "撤回指定ID的消息。传入一个消息ID，如果该消息在2分钟内且是助手发送的，则将其撤回。",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "要撤回的消息ID",
                    }
                },
                "required": ["message_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "block_user",
            "description": "拉黑用户。可以随心情使用，没有任何规则限制，但要符合角色人设。一旦调用此工具，将添加一条系统拉黑消息，用户后续发送的消息将被拒收。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]


class ToolService:
    """Service for handling LLM tool calls."""

    def __init__(self, message_service: MessageService):
        self.message_service = message_service

    async def execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        session_id: str,
        character_avatar: str,
        user_avatar: str,
    ) -> Dict[str, Any]:
        """
        Execute a tool call and return the result.
        
        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool
            session_id: Current session ID
            character_avatar: Path to character avatar
            user_avatar: Path to user avatar
            
        Returns:
            Dictionary with tool execution result
        """
        if tool_name == "get_avatar_descriptions":
            return await self.get_avatar_descriptions(character_avatar, user_avatar)
        elif tool_name == "get_image_description":
            image_id = tool_args.get("image_id")
            if not image_id:
                return {"error": "image_id is required"}
            return await self.get_image_description(image_id)
        elif tool_name == "get_recallable_messages":
            return await self.get_recallable_messages(session_id)
        elif tool_name == "recall_message_by_id":
            message_id = tool_args.get("message_id")
            if not message_id:
                return {"error": "message_id is required"}
            return await self.recall_message_by_id(session_id, message_id)
        elif tool_name == "block_user":
            return await self.block_user(session_id)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    async def get_avatar_descriptions(
        self, character_avatar: str, user_avatar: str
    ) -> Dict[str, Any]:
        """
        Get descriptions for character and user avatars.
        
        Args:
            character_avatar: Path to character avatar
            user_avatar: Path to user avatar
            
        Returns:
            Dictionary with character and user avatar descriptions
        """
        character_desc = image_alter.get_description(character_avatar)
        
        # Only return user avatar description if it's the default avatar
        # Don't return description for custom user avatars
        from src.core.models.constants import DEFAULT_USER_AVATAR
        user_desc = None
        if user_avatar == DEFAULT_USER_AVATAR:
            user_desc = image_alter.get_description(user_avatar)

        return {
            "character_avatar_description": character_desc or "图片加载失败",
            "user_avatar_description": user_desc or "用户使用了自定义头像",
        }

    async def get_image_description(self, image_id: str) -> Dict[str, Any]:
        """
        Get description for a specific image by its message ID.
        
        Args:
            image_id: Message ID of the image
            
        Returns:
            Dictionary with image description and ID
        """
        message = await self.message_service.get_message(image_id)
        
        if not message:
            return {
                "error": "图片消息不存在",
                "image_id": image_id,
            }
        
        if message.type != MessageType.IMAGE:
            return {
                "error": "指定的消息不是图片类型",
                "image_id": image_id,
            }
        
        # Get image description from image path
        image_path = message.content or ""
        description = image_alter.get_description(image_path)
        
        if description:
            return {
                "image_id": image_id,
                "description": description,
            }
        else:
            return {
                "image_id": image_id,
                "description": "图片加载失败",
            }

    async def get_recallable_messages(self, session_id: str) -> Dict[str, Any]:
        """
        Get all messages sent by assistant in the last 2 minutes that can be recalled.
        Actually returns messages from the last 1.5 minutes to account for delays.
        
        Args:
            session_id: Current session ID
            
        Returns:
            Dictionary with list of recallable messages
        """
        messages = await self.message_service.get_messages(session_id)
        current_time = datetime.now(timezone.utc).timestamp()
        # Claim 2 minutes but actually return 1.5 minutes (90 seconds)
        ninety_seconds_ago = current_time - 90

        recallable = []
        for msg in messages:
            # Must be assistant role, not recalled, and within 1.5 minutes
            if (
                msg.sender_id == "assistant"
                and not msg.is_recalled
                and msg.timestamp >= ninety_seconds_ago
                and msg.type in [MessageType.TEXT, MessageType.IMAGE]
            ):
                recallable.append(
                    {
                        "id": msg.id,
                        "content": msg.content,
                        "timestamp": msg.timestamp,
                        "type": msg.type,
                    }
                )

        return {"recallable_messages": recallable}

    async def recall_message_by_id(
        self, session_id: str, message_id: str
    ) -> Dict[str, Any]:
        """
        Recall a specific message by ID if it's within 2 minutes.
        
        Args:
            session_id: Current session ID
            message_id: ID of the message to recall
            
        Returns:
            Dictionary with recall result
        """
        message = await self.message_service.get_message(message_id)
        
        if not message:
            return {"error": "Message not found", "success": False}

        if message.session_id != session_id:
            return {"error": "Message not in this session", "success": False}

        current_time = datetime.now(timezone.utc).timestamp()
        two_minutes_ago = current_time - 120  # 2 minutes in seconds

        if message.timestamp < two_minutes_ago:
            return {"error": "Message is older than 2 minutes", "success": False}

        if message.sender_id != "assistant":
            return {"error": "Can only recall assistant messages", "success": False}

        if message.is_recalled:
            return {"error": "Message already recalled", "success": False}

        # Recall the message
        recall_msg = await self.message_service.recall_message(
            session_id=session_id,
            message_id=message_id,
            timestamp=message.timestamp,
            recalled_by="assistant",
        )

        if recall_msg:
            return {
                "success": True,
                "recalled_message_id": message_id,
                "recall_system_message_id": recall_msg.id,
            }
        else:
            return {"error": "Failed to recall message", "success": False}

    async def block_user(self, session_id: str) -> Dict[str, Any]:
        """
        Block the user by adding a SYSTEM_BLOCKED message.
        
        Args:
            session_id: Current session ID
            
        Returns:
            Dictionary with block result
        """
        # Create a blocked message
        blocked_msg = await self.message_service.send_message(
            session_id=session_id,
            sender_id="system",
            message_type=MessageType.SYSTEM_BLOCKED,
            content="",
            metadata={},
        )

        return {
            "success": True,
            "blocked": True,
            "blocked_message_id": blocked_msg.id,
        }

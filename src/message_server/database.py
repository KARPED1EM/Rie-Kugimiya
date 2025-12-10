import sqlite3
import json
import logging
from typing import List, Optional
from pathlib import Path
from contextlib import contextmanager
from .models import Message, MessageType
from ..config import database_config

logger = logging.getLogger(__name__)


class MessageDatabase:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or database_config.path
        self._ensure_database_exists()

    def _ensure_database_exists(self):
        db_path = Path(self.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    sender_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_timestamp
                ON messages(conversation_id, timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sender
                ON messages(sender_id)
            """)
            conn.commit()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def save_message(self, message: Message) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO messages (id, conversation_id, sender_id, type, content, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    message.id,
                    message.conversation_id,
                    message.sender_id,
                    message.type,
                    message.content,
                    message.timestamp,
                    json.dumps(message.metadata)
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving message: {e}", exc_info=True)
            return False

    def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        after_timestamp: Optional[float] = None
    ) -> List[Message]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM messages WHERE conversation_id = ?"
                params = [conversation_id]

                if after_timestamp is not None:
                    query += " AND timestamp > ?"
                    params.append(after_timestamp)

                query += " ORDER BY timestamp ASC"

                if limit is not None:
                    query += " LIMIT ?"
                    params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                messages = []
                for row in rows:
                    metadata = json.loads(row['metadata']) if row['metadata'] else {}
                    messages.append(Message(
                        id=row['id'],
                        conversation_id=row['conversation_id'],
                        sender_id=row['sender_id'],
                        type=MessageType(row['type']),
                        content=row['content'],
                        timestamp=row['timestamp'],
                        metadata=metadata
                    ))
                return messages
        except Exception as e:
            logger.error(f"Error getting messages: {e}", exc_info=True)
            return []

    def get_message_by_id(self, message_id: str) -> Optional[Message]:
        """根据ID查询单条消息"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
                row = cursor.fetchone()

                if row:
                    metadata = json.loads(row['metadata']) if row['metadata'] else {}
                    return Message(
                        id=row['id'],
                        conversation_id=row['conversation_id'],
                        sender_id=row['sender_id'],
                        type=MessageType(row['type']),
                        content=row['content'],
                        timestamp=row['timestamp'],
                        metadata=metadata
                    )
                return None
        except Exception as e:
            logger.error(f"Error getting message by id: {e}", exc_info=True)
            return None

    def clear_conversation(self, conversation_id: str) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error clearing conversation: {e}", exc_info=True)
            return False


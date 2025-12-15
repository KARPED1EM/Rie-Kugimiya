import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)


class DatabaseConnection:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._prepare_database_path()
        self._ensure_schema()

    def _prepare_database_path(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _ensure_schema(self):
        with self.transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    sender_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    is_recalled BOOLEAN DEFAULT FALSE,
                    is_read BOOLEAN DEFAULT FALSE,
                    timestamp REAL NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_timestamp
                ON messages(session_id, timestamp)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sender
                ON messages(sender_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_type
                ON messages(type)
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS characters (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    avatar TEXT,
                    persona TEXT NOT NULL,
                    is_builtin BOOLEAN,

                    timeline_hesitation_probability REAL,
                    timeline_hesitation_cycles_min INTEGER,
                    timeline_hesitation_cycles_max INTEGER,
                    timeline_hesitation_duration_min INTEGER,
                    timeline_hesitation_duration_max INTEGER,
                    timeline_hesitation_gap_min INTEGER,
                    timeline_hesitation_gap_max INTEGER,

                    timeline_typing_lead_time_threshold_1 INTEGER,
                    timeline_typing_lead_time_1 INTEGER,
                    timeline_typing_lead_time_threshold_2 INTEGER,
                    timeline_typing_lead_time_2 INTEGER,
                    timeline_typing_lead_time_threshold_3 INTEGER,
                    timeline_typing_lead_time_3 INTEGER,
                    timeline_typing_lead_time_threshold_4 INTEGER,
                    timeline_typing_lead_time_4 INTEGER,
                    timeline_typing_lead_time_threshold_5 INTEGER,
                    timeline_typing_lead_time_5 INTEGER,
                    timeline_typing_lead_time_default INTEGER,

                    timeline_entry_delay_min INTEGER,
                    timeline_entry_delay_max INTEGER,

                    timeline_initial_delay_weight_1 REAL,
                    timeline_initial_delay_range_1_min INTEGER,
                    timeline_initial_delay_range_1_max INTEGER,
                    timeline_initial_delay_weight_2 REAL,
                    timeline_initial_delay_range_2_min INTEGER,
                    timeline_initial_delay_range_2_max INTEGER,
                    timeline_initial_delay_weight_3 REAL,
                    timeline_initial_delay_range_3_min INTEGER,
                    timeline_initial_delay_range_3_max INTEGER,
                    timeline_initial_delay_range_4_min INTEGER,
                    timeline_initial_delay_range_4_max INTEGER,

                    segmenter_enable BOOLEAN,
                    segmenter_max_length INTEGER,

                    typo_enable BOOLEAN,
                    typo_base_rate REAL,
                    typo_recall_rate REAL,

                    recall_enable BOOLEAN,
                    recall_delay REAL,
                    recall_retype_delay REAL,

                    pause_min_duration REAL,
                    pause_max_duration REAL,

                    sticker_packs TEXT,
                    sticker_send_probability REAL,
                    sticker_confidence_threshold_positive REAL,
                    sticker_confidence_threshold_neutral REAL,
                    sticker_confidence_threshold_negative REAL,

                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    character_id TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
                    UNIQUE(character_id)
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_active_session
                ON sessions(is_active)
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id TEXT PRIMARY KEY,
                    avatar_data TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA busy_timeout = 30000")
            conn.execute("PRAGMA foreign_keys = ON")
        except Exception:
            pass
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA busy_timeout = 30000")
            conn.execute("PRAGMA foreign_keys = ON")
        except Exception:
            pass
        try:
            yield conn
        finally:
            conn.close()

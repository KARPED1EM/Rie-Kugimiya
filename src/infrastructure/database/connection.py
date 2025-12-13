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
                    is_builtin BOOLEAN DEFAULT FALSE,

                    hesitation_probability REAL DEFAULT 0.15,
                    hesitation_cycles_min INTEGER DEFAULT 1,
                    hesitation_cycles_max INTEGER DEFAULT 2,
                    hesitation_duration_min INTEGER DEFAULT 1500,
                    hesitation_duration_max INTEGER DEFAULT 5000,
                    hesitation_gap_min INTEGER DEFAULT 500,
                    hesitation_gap_max INTEGER DEFAULT 2000,

                    typing_lead_time_threshold_1 INTEGER DEFAULT 6,
                    typing_lead_time_1 INTEGER DEFAULT 1200,
                    typing_lead_time_threshold_2 INTEGER DEFAULT 15,
                    typing_lead_time_2 INTEGER DEFAULT 2000,
                    typing_lead_time_threshold_3 INTEGER DEFAULT 28,
                    typing_lead_time_3 INTEGER DEFAULT 3800,
                    typing_lead_time_threshold_4 INTEGER DEFAULT 34,
                    typing_lead_time_4 INTEGER DEFAULT 6000,
                    typing_lead_time_threshold_5 INTEGER DEFAULT 50,
                    typing_lead_time_5 INTEGER DEFAULT 8800,
                    typing_lead_time_default INTEGER DEFAULT 2500,

                    entry_delay_min INTEGER DEFAULT 200,
                    entry_delay_max INTEGER DEFAULT 2000,

                    initial_delay_weight_1 REAL DEFAULT 0.45,
                    initial_delay_range_1_min INTEGER DEFAULT 3,
                    initial_delay_range_1_max INTEGER DEFAULT 4,
                    initial_delay_weight_2 REAL DEFAULT 0.75,
                    initial_delay_range_2_min INTEGER DEFAULT 4,
                    initial_delay_range_2_max INTEGER DEFAULT 6,
                    initial_delay_weight_3 REAL DEFAULT 0.93,
                    initial_delay_range_3_min INTEGER DEFAULT 6,
                    initial_delay_range_3_max INTEGER DEFAULT 7,
                    initial_delay_range_4_min INTEGER DEFAULT 8,
                    initial_delay_range_4_max INTEGER DEFAULT 9,

                    enable_segmentation BOOLEAN DEFAULT TRUE,
                    enable_typo BOOLEAN DEFAULT TRUE,
                    enable_recall BOOLEAN DEFAULT TRUE,
                    enable_emotion_detection BOOLEAN DEFAULT TRUE,

                    max_segment_length INTEGER DEFAULT 50,
                    min_pause_duration REAL DEFAULT 0.8,
                    max_pause_duration REAL DEFAULT 6.0,

                    base_typo_rate REAL DEFAULT 0.05,
                    typo_recall_rate REAL DEFAULT 0.75,
                    recall_delay REAL DEFAULT 2.0,
                    retype_delay REAL DEFAULT 2.5,

                    sticker_packs TEXT,
                    sticker_send_probability REAL DEFAULT 0.4,
                    sticker_confidence_threshold_positive REAL DEFAULT 0.6,
                    sticker_confidence_threshold_neutral REAL DEFAULT 0.7,
                    sticker_confidence_threshold_negative REAL DEFAULT 0.8,

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

            self._migrate_emoticon_to_sticker_packs(cursor)
            self._migrate_add_sticker_config_columns(cursor)

            conn.commit()

    def _migrate_emoticon_to_sticker_packs(self, cursor):
        cursor.execute("PRAGMA table_info(characters)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "emoticon_packs" in columns and "sticker_packs" not in columns:
            cursor.execute("""
                ALTER TABLE characters
                RENAME COLUMN emoticon_packs TO sticker_packs
            """)
            logger.info("Migrated emoticon_packs to sticker_packs")
        elif "emoticon_packs" not in columns and "sticker_packs" not in columns:
            cursor.execute("""
                ALTER TABLE characters
                ADD COLUMN sticker_packs TEXT
            """)
            logger.info("Added sticker_packs column")

    def _migrate_add_sticker_config_columns(self, cursor):
        cursor.execute("PRAGMA table_info(characters)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "sticker_send_probability" not in columns:
            cursor.execute("""
                ALTER TABLE characters
                ADD COLUMN sticker_send_probability REAL DEFAULT 0.4
            """)
            logger.info("Added sticker_send_probability column")
        
        if "sticker_confidence_threshold_positive" not in columns:
            cursor.execute("""
                ALTER TABLE characters
                ADD COLUMN sticker_confidence_threshold_positive REAL DEFAULT 0.6
            """)
            logger.info("Added sticker_confidence_threshold_positive column")
        
        if "sticker_confidence_threshold_neutral" not in columns:
            cursor.execute("""
                ALTER TABLE characters
                ADD COLUMN sticker_confidence_threshold_neutral REAL DEFAULT 0.7
            """)
            logger.info("Added sticker_confidence_threshold_neutral column")
        
        if "sticker_confidence_threshold_negative" not in columns:
            cursor.execute("""
                ALTER TABLE characters
                ADD COLUMN sticker_confidence_threshold_negative REAL DEFAULT 0.8
            """)
            logger.info("Added sticker_confidence_threshold_negative column")

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

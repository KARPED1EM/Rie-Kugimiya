import json
import logging
from typing import List, Optional
from datetime import datetime
from src.core.models.character import Character
from src.infrastructure.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class CharacterRepository(BaseRepository[Character]):
    async def get_by_id(self, id: str) -> Optional[Character]:
        try:
            with self.conn_mgr.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM characters WHERE id = ?", (id,))
                row = cursor.fetchone()
                if row:
                    return self._row_to_character(row)
                return None
        except Exception as e:
            logger.error(f"Error getting character by id: {e}", exc_info=True)
            return None

    async def get_all(self) -> List[Character]:
        try:
            with self.conn_mgr.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM characters ORDER BY created_at ASC")
                rows = cursor.fetchall()
                return [self._row_to_character(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting all characters: {e}", exc_info=True)
            return []

    async def create(self, character: Character) -> bool:
        try:
            with self.conn_mgr.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO characters (
                        id, name, avatar, persona, is_builtin,
                        hesitation_probability, hesitation_cycles_min, hesitation_cycles_max,
                        hesitation_duration_min, hesitation_duration_max,
                        hesitation_gap_min, hesitation_gap_max,
                        typing_lead_time_threshold_1, typing_lead_time_1,
                        typing_lead_time_threshold_2, typing_lead_time_2,
                        typing_lead_time_threshold_3, typing_lead_time_3,
                        typing_lead_time_threshold_4, typing_lead_time_4,
                        typing_lead_time_threshold_5, typing_lead_time_5,
                        typing_lead_time_default,
                        entry_delay_min, entry_delay_max,
                        initial_delay_weight_1, initial_delay_range_1_min, initial_delay_range_1_max,
                        initial_delay_weight_2, initial_delay_range_2_min, initial_delay_range_2_max,
                        initial_delay_weight_3, initial_delay_range_3_min, initial_delay_range_3_max,
                        initial_delay_range_4_min, initial_delay_range_4_max,
                        enable_segmentation, enable_typo, enable_recall, enable_emotion_detection,
                        max_segment_length, min_pause_duration, max_pause_duration,
                        base_typo_rate, typo_recall_rate, recall_delay, retype_delay,
                        sticker_packs, sticker_send_probability,
                        sticker_confidence_threshold_positive, sticker_confidence_threshold_neutral,
                        sticker_confidence_threshold_negative
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    character.id, character.name, character.avatar, character.persona, character.is_builtin,
                    character.hesitation_probability, character.hesitation_cycles_min, character.hesitation_cycles_max,
                    character.hesitation_duration_min, character.hesitation_duration_max,
                    character.hesitation_gap_min, character.hesitation_gap_max,
                    character.typing_lead_time_threshold_1, character.typing_lead_time_1,
                    character.typing_lead_time_threshold_2, character.typing_lead_time_2,
                    character.typing_lead_time_threshold_3, character.typing_lead_time_3,
                    character.typing_lead_time_threshold_4, character.typing_lead_time_4,
                    character.typing_lead_time_threshold_5, character.typing_lead_time_5,
                    character.typing_lead_time_default,
                    character.entry_delay_min, character.entry_delay_max,
                    character.initial_delay_weight_1, character.initial_delay_range_1_min, character.initial_delay_range_1_max,
                    character.initial_delay_weight_2, character.initial_delay_range_2_min, character.initial_delay_range_2_max,
                    character.initial_delay_weight_3, character.initial_delay_range_3_min, character.initial_delay_range_3_max,
                    character.initial_delay_range_4_min, character.initial_delay_range_4_max,
                    character.enable_segmentation, character.enable_typo, character.enable_recall, character.enable_emotion_detection,
                    character.max_segment_length, character.min_pause_duration, character.max_pause_duration,
                    character.base_typo_rate, character.typo_recall_rate, character.recall_delay, character.retype_delay,
                    json.dumps(character.sticker_packs), character.sticker_send_probability,
                    character.sticker_confidence_threshold_positive, character.sticker_confidence_threshold_neutral,
                    character.sticker_confidence_threshold_negative
                ))
                return True
        except Exception as e:
            logger.error(f"Error creating character: {e}", exc_info=True)
            return False

    async def update(self, character: Character) -> bool:
        try:
            with self.conn_mgr.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE characters SET
                        name = ?, avatar = ?, persona = ?,
                        hesitation_probability = ?, hesitation_cycles_min = ?, hesitation_cycles_max = ?,
                        hesitation_duration_min = ?, hesitation_duration_max = ?,
                        hesitation_gap_min = ?, hesitation_gap_max = ?,
                        typing_lead_time_threshold_1 = ?, typing_lead_time_1 = ?,
                        typing_lead_time_threshold_2 = ?, typing_lead_time_2 = ?,
                        typing_lead_time_threshold_3 = ?, typing_lead_time_3 = ?,
                        typing_lead_time_threshold_4 = ?, typing_lead_time_4 = ?,
                        typing_lead_time_threshold_5 = ?, typing_lead_time_5 = ?,
                        typing_lead_time_default = ?,
                        entry_delay_min = ?, entry_delay_max = ?,
                        initial_delay_weight_1 = ?, initial_delay_range_1_min = ?, initial_delay_range_1_max = ?,
                        initial_delay_weight_2 = ?, initial_delay_range_2_min = ?, initial_delay_range_2_max = ?,
                        initial_delay_weight_3 = ?, initial_delay_range_3_min = ?, initial_delay_range_3_max = ?,
                        initial_delay_range_4_min = ?, initial_delay_range_4_max = ?,
                        enable_segmentation = ?, enable_typo = ?, enable_recall = ?, enable_emotion_detection = ?,
                        max_segment_length = ?, min_pause_duration = ?, max_pause_duration = ?,
                        base_typo_rate = ?, typo_recall_rate = ?, recall_delay = ?, retype_delay = ?,
                        sticker_packs = ?, sticker_send_probability = ?,
                        sticker_confidence_threshold_positive = ?, sticker_confidence_threshold_neutral = ?,
                        sticker_confidence_threshold_negative = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    character.name, character.avatar, character.persona,
                    character.hesitation_probability, character.hesitation_cycles_min, character.hesitation_cycles_max,
                    character.hesitation_duration_min, character.hesitation_duration_max,
                    character.hesitation_gap_min, character.hesitation_gap_max,
                    character.typing_lead_time_threshold_1, character.typing_lead_time_1,
                    character.typing_lead_time_threshold_2, character.typing_lead_time_2,
                    character.typing_lead_time_threshold_3, character.typing_lead_time_3,
                    character.typing_lead_time_threshold_4, character.typing_lead_time_4,
                    character.typing_lead_time_threshold_5, character.typing_lead_time_5,
                    character.typing_lead_time_default,
                    character.entry_delay_min, character.entry_delay_max,
                    character.initial_delay_weight_1, character.initial_delay_range_1_min, character.initial_delay_range_1_max,
                    character.initial_delay_weight_2, character.initial_delay_range_2_min, character.initial_delay_range_2_max,
                    character.initial_delay_weight_3, character.initial_delay_range_3_min, character.initial_delay_range_3_max,
                    character.initial_delay_range_4_min, character.initial_delay_range_4_max,
                    character.enable_segmentation, character.enable_typo, character.enable_recall, character.enable_emotion_detection,
                    character.max_segment_length, character.min_pause_duration, character.max_pause_duration,
                    character.base_typo_rate, character.typo_recall_rate, character.recall_delay, character.retype_delay,
                    json.dumps(character.sticker_packs), character.sticker_send_probability,
                    character.sticker_confidence_threshold_positive, character.sticker_confidence_threshold_neutral,
                    character.sticker_confidence_threshold_negative,
                    character.id
                ))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating character: {e}", exc_info=True)
            return False

    async def delete(self, id: str) -> bool:
        try:
            with self.conn_mgr.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM characters WHERE id = ?", (id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting character: {e}", exc_info=True)
            return False

    def _row_to_character(self, row) -> Character:
        sticker_packs = json.loads(row['sticker_packs']) if row['sticker_packs'] else []
        return Character(
            id=row['id'],
            name=row['name'],
            avatar=row['avatar'],
            persona=row['persona'],
            is_builtin=bool(row['is_builtin']),
            hesitation_probability=row['hesitation_probability'],
            hesitation_cycles_min=row['hesitation_cycles_min'],
            hesitation_cycles_max=row['hesitation_cycles_max'],
            hesitation_duration_min=row['hesitation_duration_min'],
            hesitation_duration_max=row['hesitation_duration_max'],
            hesitation_gap_min=row['hesitation_gap_min'],
            hesitation_gap_max=row['hesitation_gap_max'],
            typing_lead_time_threshold_1=row['typing_lead_time_threshold_1'],
            typing_lead_time_1=row['typing_lead_time_1'],
            typing_lead_time_threshold_2=row['typing_lead_time_threshold_2'],
            typing_lead_time_2=row['typing_lead_time_2'],
            typing_lead_time_threshold_3=row['typing_lead_time_threshold_3'],
            typing_lead_time_3=row['typing_lead_time_3'],
            typing_lead_time_threshold_4=row['typing_lead_time_threshold_4'],
            typing_lead_time_4=row['typing_lead_time_4'],
            typing_lead_time_threshold_5=row['typing_lead_time_threshold_5'],
            typing_lead_time_5=row['typing_lead_time_5'],
            typing_lead_time_default=row['typing_lead_time_default'],
            entry_delay_min=row['entry_delay_min'],
            entry_delay_max=row['entry_delay_max'],
            initial_delay_weight_1=row['initial_delay_weight_1'],
            initial_delay_range_1_min=row['initial_delay_range_1_min'],
            initial_delay_range_1_max=row['initial_delay_range_1_max'],
            initial_delay_weight_2=row['initial_delay_weight_2'],
            initial_delay_range_2_min=row['initial_delay_range_2_min'],
            initial_delay_range_2_max=row['initial_delay_range_2_max'],
            initial_delay_weight_3=row['initial_delay_weight_3'],
            initial_delay_range_3_min=row['initial_delay_range_3_min'],
            initial_delay_range_3_max=row['initial_delay_range_3_max'],
            initial_delay_range_4_min=row['initial_delay_range_4_min'],
            initial_delay_range_4_max=row['initial_delay_range_4_max'],
            enable_segmentation=bool(row['enable_segmentation']),
            enable_typo=bool(row['enable_typo']),
            enable_recall=bool(row['enable_recall']),
            enable_emotion_detection=bool(row['enable_emotion_detection']),
            max_segment_length=row['max_segment_length'],
            min_pause_duration=row['min_pause_duration'],
            max_pause_duration=row['max_pause_duration'],
            base_typo_rate=row['base_typo_rate'],
            typo_recall_rate=row['typo_recall_rate'],
            recall_delay=row['recall_delay'],
            retype_delay=row['retype_delay'],
            sticker_packs=sticker_packs,
            sticker_send_probability=row['sticker_send_probability'],
            sticker_confidence_threshold_positive=row['sticker_confidence_threshold_positive'],
            sticker_confidence_threshold_neutral=row['sticker_confidence_threshold_neutral'],
            sticker_confidence_threshold_negative=row['sticker_confidence_threshold_negative'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )

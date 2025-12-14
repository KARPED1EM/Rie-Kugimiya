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
                        timeline_hesitation_probability, timeline_hesitation_cycles_min, timeline_hesitation_cycles_max,
                        timeline_hesitation_duration_min, timeline_hesitation_duration_max,
                        timeline_hesitation_gap_min, timeline_hesitation_gap_max,
                        timeline_typing_lead_time_threshold_1, timeline_typing_lead_time_1,
                        timeline_typing_lead_time_threshold_2, timeline_typing_lead_time_2,
                        timeline_typing_lead_time_threshold_3, timeline_typing_lead_time_3,
                        timeline_typing_lead_time_threshold_4, timeline_typing_lead_time_4,
                        timeline_typing_lead_time_threshold_5, timeline_typing_lead_time_5,
                        timeline_typing_lead_time_default,
                        timeline_entry_delay_min, timeline_entry_delay_max,
                        timeline_initial_delay_weight_1, timeline_initial_delay_range_1_min, timeline_initial_delay_range_1_max,
                        timeline_initial_delay_weight_2, timeline_initial_delay_range_2_min, timeline_initial_delay_range_2_max,
                        timeline_initial_delay_weight_3, timeline_initial_delay_range_3_min, timeline_initial_delay_range_3_max,
                        timeline_initial_delay_range_4_min, timeline_initial_delay_range_4_max,
                        segmenter_enable, segmenter_max_length,
                        typo_enable, typo_base_rate, typo_recall_rate,
                        recall_enable, recall_delay, recall_retype_delay,
                        pause_min_duration, pause_max_duration,
                        sticker_packs, sticker_send_probability,
                        sticker_confidence_threshold_positive, sticker_confidence_threshold_neutral,
                        sticker_confidence_threshold_negative
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    character.id, character.name, character.avatar, character.persona, character.is_builtin,
                    character.timeline_hesitation_probability, character.timeline_hesitation_cycles_min, character.timeline_hesitation_cycles_max,
                    character.timeline_hesitation_duration_min, character.timeline_hesitation_duration_max,
                    character.timeline_hesitation_gap_min, character.timeline_hesitation_gap_max,
                    character.timeline_typing_lead_time_threshold_1, character.timeline_typing_lead_time_1,
                    character.timeline_typing_lead_time_threshold_2, character.timeline_typing_lead_time_2,
                    character.timeline_typing_lead_time_threshold_3, character.timeline_typing_lead_time_3,
                    character.timeline_typing_lead_time_threshold_4, character.timeline_typing_lead_time_4,
                    character.timeline_typing_lead_time_threshold_5, character.timeline_typing_lead_time_5,
                    character.timeline_typing_lead_time_default,
                    character.timeline_entry_delay_min, character.timeline_entry_delay_max,
                    character.timeline_initial_delay_weight_1, character.timeline_initial_delay_range_1_min, character.timeline_initial_delay_range_1_max,
                    character.timeline_initial_delay_weight_2, character.timeline_initial_delay_range_2_min, character.timeline_initial_delay_range_2_max,
                    character.timeline_initial_delay_weight_3, character.timeline_initial_delay_range_3_min, character.timeline_initial_delay_range_3_max,
                    character.timeline_initial_delay_range_4_min, character.timeline_initial_delay_range_4_max,
                    character.segmenter_enable, character.segmenter_max_length,
                    character.typo_enable, character.typo_base_rate, character.typo_recall_rate,
                    character.recall_enable, character.recall_delay, character.recall_retype_delay,
                    character.pause_min_duration, character.pause_max_duration,
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
                        timeline_hesitation_probability = ?, timeline_hesitation_cycles_min = ?, timeline_hesitation_cycles_max = ?,
                        timeline_hesitation_duration_min = ?, timeline_hesitation_duration_max = ?,
                        timeline_hesitation_gap_min = ?, timeline_hesitation_gap_max = ?,
                        timeline_typing_lead_time_threshold_1 = ?, timeline_typing_lead_time_1 = ?,
                        timeline_typing_lead_time_threshold_2 = ?, timeline_typing_lead_time_2 = ?,
                        timeline_typing_lead_time_threshold_3 = ?, timeline_typing_lead_time_3 = ?,
                        timeline_typing_lead_time_threshold_4 = ?, timeline_typing_lead_time_4 = ?,
                        timeline_typing_lead_time_threshold_5 = ?, timeline_typing_lead_time_5 = ?,
                        timeline_typing_lead_time_default = ?,
                        timeline_entry_delay_min = ?, timeline_entry_delay_max = ?,
                        timeline_initial_delay_weight_1 = ?, timeline_initial_delay_range_1_min = ?, timeline_initial_delay_range_1_max = ?,
                        timeline_initial_delay_weight_2 = ?, timeline_initial_delay_range_2_min = ?, timeline_initial_delay_range_2_max = ?,
                        timeline_initial_delay_weight_3 = ?, timeline_initial_delay_range_3_min = ?, timeline_initial_delay_range_3_max = ?,
                        timeline_initial_delay_range_4_min = ?, timeline_initial_delay_range_4_max = ?,
                        segmenter_enable = ?, segmenter_max_length = ?,
                        typo_enable = ?, typo_base_rate = ?, typo_recall_rate = ?,
                        recall_enable = ?, recall_delay = ?, recall_retype_delay = ?,
                        pause_min_duration = ?, pause_max_duration = ?,
                        sticker_packs = ?, sticker_send_probability = ?,
                        sticker_confidence_threshold_positive = ?, sticker_confidence_threshold_neutral = ?,
                        sticker_confidence_threshold_negative = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    character.name, character.avatar, character.persona,
                    character.timeline_hesitation_probability, character.timeline_hesitation_cycles_min, character.timeline_hesitation_cycles_max,
                    character.timeline_hesitation_duration_min, character.timeline_hesitation_duration_max,
                    character.timeline_hesitation_gap_min, character.timeline_hesitation_gap_max,
                    character.timeline_typing_lead_time_threshold_1, character.timeline_typing_lead_time_1,
                    character.timeline_typing_lead_time_threshold_2, character.timeline_typing_lead_time_2,
                    character.timeline_typing_lead_time_threshold_3, character.timeline_typing_lead_time_3,
                    character.timeline_typing_lead_time_threshold_4, character.timeline_typing_lead_time_4,
                    character.timeline_typing_lead_time_threshold_5, character.timeline_typing_lead_time_5,
                    character.timeline_typing_lead_time_default,
                    character.timeline_entry_delay_min, character.timeline_entry_delay_max,
                    character.timeline_initial_delay_weight_1, character.timeline_initial_delay_range_1_min, character.timeline_initial_delay_range_1_max,
                    character.timeline_initial_delay_weight_2, character.timeline_initial_delay_range_2_min, character.timeline_initial_delay_range_2_max,
                    character.timeline_initial_delay_weight_3, character.timeline_initial_delay_range_3_min, character.timeline_initial_delay_range_3_max,
                    character.timeline_initial_delay_range_4_min, character.timeline_initial_delay_range_4_max,
                    character.segmenter_enable, character.segmenter_max_length,
                    character.typo_enable, character.typo_base_rate, character.typo_recall_rate,
                    character.recall_enable, character.recall_delay, character.recall_retype_delay,
                    character.pause_min_duration, character.pause_max_duration,
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
            timeline_hesitation_probability=row['timeline_hesitation_probability'],
            timeline_hesitation_cycles_min=row['timeline_hesitation_cycles_min'],
            timeline_hesitation_cycles_max=row['timeline_hesitation_cycles_max'],
            timeline_hesitation_duration_min=row['timeline_hesitation_duration_min'],
            timeline_hesitation_duration_max=row['timeline_hesitation_duration_max'],
            timeline_hesitation_gap_min=row['timeline_hesitation_gap_min'],
            timeline_hesitation_gap_max=row['timeline_hesitation_gap_max'],
            timeline_typing_lead_time_threshold_1=row['timeline_typing_lead_time_threshold_1'],
            timeline_typing_lead_time_1=row['timeline_typing_lead_time_1'],
            timeline_typing_lead_time_threshold_2=row['timeline_typing_lead_time_threshold_2'],
            timeline_typing_lead_time_2=row['timeline_typing_lead_time_2'],
            timeline_typing_lead_time_threshold_3=row['timeline_typing_lead_time_threshold_3'],
            timeline_typing_lead_time_3=row['timeline_typing_lead_time_3'],
            timeline_typing_lead_time_threshold_4=row['timeline_typing_lead_time_threshold_4'],
            timeline_typing_lead_time_4=row['timeline_typing_lead_time_4'],
            timeline_typing_lead_time_threshold_5=row['timeline_typing_lead_time_threshold_5'],
            timeline_typing_lead_time_5=row['timeline_typing_lead_time_5'],
            timeline_typing_lead_time_default=row['timeline_typing_lead_time_default'],
            timeline_entry_delay_min=row['timeline_entry_delay_min'],
            timeline_entry_delay_max=row['timeline_entry_delay_max'],
            timeline_initial_delay_weight_1=row['timeline_initial_delay_weight_1'],
            timeline_initial_delay_range_1_min=row['timeline_initial_delay_range_1_min'],
            timeline_initial_delay_range_1_max=row['timeline_initial_delay_range_1_max'],
            timeline_initial_delay_weight_2=row['timeline_initial_delay_weight_2'],
            timeline_initial_delay_range_2_min=row['timeline_initial_delay_range_2_min'],
            timeline_initial_delay_range_2_max=row['timeline_initial_delay_range_2_max'],
            timeline_initial_delay_weight_3=row['timeline_initial_delay_weight_3'],
            timeline_initial_delay_range_3_min=row['timeline_initial_delay_range_3_min'],
            timeline_initial_delay_range_3_max=row['timeline_initial_delay_range_3_max'],
            timeline_initial_delay_range_4_min=row['timeline_initial_delay_range_4_min'],
            timeline_initial_delay_range_4_max=row['timeline_initial_delay_range_4_max'],
            segmenter_enable=bool(row['segmenter_enable']),
            segmenter_max_length=row['segmenter_max_length'],
            typo_enable=bool(row['typo_enable']),
            typo_base_rate=row['typo_base_rate'],
            typo_recall_rate=row['typo_recall_rate'],
            recall_enable=bool(row['recall_enable']),
            recall_delay=row['recall_delay'],
            recall_retype_delay=row['recall_retype_delay'],
            pause_min_duration=row['pause_min_duration'],
            pause_max_duration=row['pause_max_duration'],
            sticker_packs=sticker_packs,
            sticker_send_probability=row['sticker_send_probability'],
            sticker_confidence_threshold_positive=row['sticker_confidence_threshold_positive'],
            sticker_confidence_threshold_neutral=row['sticker_confidence_threshold_neutral'],
            sticker_confidence_threshold_negative=row['sticker_confidence_threshold_negative'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )

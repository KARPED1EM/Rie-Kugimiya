// @ts-check

/**
 * @typedef {Object} Message
 * @property {string} id
 * @property {string} session_id
 * @property {string} sender_id
 * @property {"text"|"image"|"video"|"audio"|"system-recall"|"system-time"|"system-hint"|"system-emotion"|"system-typing"} type
 * @property {string} content
 * @property {Record<string, any>} metadata
 * @property {boolean} is_recalled
 * @property {boolean} is_read
 * @property {number} timestamp
 */

/**
 * @typedef {Object} Character
 * @property {string} id
 * @property {string} name
 * @property {string} avatar
 * @property {string} persona
 * @property {boolean} is_builtin
 * @property {number} hesitation_probability
 * @property {number} hesitation_cycles_min
 * @property {number} hesitation_cycles_max
 * @property {number} hesitation_duration_min
 * @property {number} hesitation_duration_max
 * @property {number} hesitation_gap_min
 * @property {number} hesitation_gap_max
 * @property {number} typing_lead_time_threshold_1
 * @property {number} typing_lead_time_1
 * @property {number} typing_lead_time_threshold_2
 * @property {number} typing_lead_time_2
 * @property {number} typing_lead_time_threshold_3
 * @property {number} typing_lead_time_3
 * @property {number} typing_lead_time_threshold_4
 * @property {number} typing_lead_time_4
 * @property {number} typing_lead_time_threshold_5
 * @property {number} typing_lead_time_5
 * @property {number} typing_lead_time_default
 * @property {number} entry_delay_min
 * @property {number} entry_delay_max
 * @property {number} initial_delay_weight_1
 * @property {number} initial_delay_range_1_min
 * @property {number} initial_delay_range_1_max
 * @property {number} initial_delay_weight_2
 * @property {number} initial_delay_range_2_min
 * @property {number} initial_delay_range_2_max
 * @property {number} initial_delay_weight_3
 * @property {number} initial_delay_range_3_min
 * @property {number} initial_delay_range_3_max
 * @property {number} initial_delay_range_4_min
 * @property {number} initial_delay_range_4_max
 * @property {boolean} enable_segmentation
 * @property {boolean} enable_typo
 * @property {boolean} enable_recall
 * @property {boolean} enable_emotion_detection
 * @property {number} max_segment_length
 * @property {number} min_pause_duration
 * @property {number} max_pause_duration
 * @property {number} base_typo_rate
 * @property {number} typo_recall_rate
 * @property {number} recall_delay
 * @property {number} retype_delay
 * @property {string[]} emoticon_packs
 */

/**
 * @typedef {Object} Session
 * @property {string} id
 * @property {string} character_id
 * @property {boolean} is_active
 */

/**
 * @typedef {Object} WsEvent
 * @property {string} type
 * @property {any} data
 */

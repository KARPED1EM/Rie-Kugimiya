import random
from pathlib import Path
from typing import Tuple, Dict, List, Optional, Any
from src.infrastructure.utils.logger import unified_logger, LogCategory


class IntentPredictor:
    _instance = None
    _model = None
    _tokenizer = None
    _id2intent = None
    _model_loaded = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.model_path = (
            Path(__file__).parent.parent.parent.parent
            / "models"
            / "wechat_intent_model"
        )
        self._load_model()

    def _load_model(self):
        if self._model_loaded:
            return

        try:
            import json
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch

            if not self.model_path.exists():
                unified_logger.warning(
                    "BERT model not found, using fallback keyword matching",
                    category=LogCategory.BEHAVIOR,
                    metadata={"model_path": str(self.model_path)},
                )
                self._model_loaded = True
                return

            mapping_file = self.model_path / "intent_mapping.json"
            if not mapping_file.exists():
                unified_logger.warning(
                    "Intent mapping not found",
                    category=LogCategory.BEHAVIOR,
                    metadata={"mapping_file": str(mapping_file)},
                )
                self._model_loaded = True
                return

            with open(mapping_file, "r", encoding="utf-8") as f:
                mapping = json.load(f)
                self._id2intent = {int(k): v for k, v in mapping["id2intent"].items()}

            self._tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
            self._model = AutoModelForSequenceClassification.from_pretrained(
                str(self.model_path)
            )
            self._model.eval()

            unified_logger.info(
                "BERT intent model loaded successfully",
                category=LogCategory.BEHAVIOR,
                metadata={
                    "model_path": str(self.model_path),
                    "num_intents": len(self._id2intent),
                },
            )
            self._model_loaded = True

        except Exception as e:
            unified_logger.error(
                f"Failed to load BERT model: {e}",
                category=LogCategory.BEHAVIOR,
                metadata={"model_path": str(self.model_path)},
            )
            self._model_loaded = True

    def predict(self, text: str) -> Tuple[str, float]:
        use_bert = (
            self._model is not None
            and self._tokenizer is not None
            and self._id2intent is not None
        )

        if use_bert:
            try:
                import torch

                inputs = self._tokenizer(
                    text, return_tensors="pt", truncation=True, max_length=128
                )

                with torch.no_grad():
                    outputs = self._model(**inputs)
                    logits = outputs.logits
                    probs = torch.nn.functional.softmax(logits, dim=-1)
                    confidence, predicted_id = torch.max(probs, dim=-1)

                predicted_id = predicted_id.item()
                confidence = confidence.item()
                intent = self._id2intent.get(predicted_id, "未知意图")

                return intent, confidence

            except Exception as e:
                unified_logger.error(
                    f"BERT prediction failed: {e}",
                    category=LogCategory.BEHAVIOR,
                )
                return self._fallback_predict(text)
        else:
            return self._fallback_predict(text)

    def _fallback_predict(self, text: str) -> Tuple[str, float]:
        if any(word in text for word in ["你好", "您好", "hi", "hello"]):
            return "招呼用语", 0.95
        elif any(word in text for word in ["谢谢", "感谢", "多谢"]):
            return "礼貌用语", 0.90
        elif any(word in text for word in ["好的", "可以", "行", "没问题"]):
            return "肯定(好的)", 0.85
        elif any(word in text for word in ["不", "不要", "不用", "不需要"]):
            return "否定(不需要)", 0.80
        elif any(word in text for word in ["什么时候", "几点", "时间"]):
            return "疑问(时间)", 0.75
        elif any(word in text for word in ["在哪", "地址", "位置"]):
            return "疑问(地址)", 0.75
        else:
            return "未知意图", 0.30


class StickerSelector:
    CONFIDENCE_THRESHOLDS = {
        "positive": 0.7,
        "neutral": 0.8,
        "negative": 0.9,
        "default": 0.8,
    }

    POSITIVE_EMOTIONS = ["happy", "excited", "playful", "affectionate", "surprised"]
    NEUTRAL_EMOTIONS = ["neutral", "confused", "shy", "bored", "caring"]
    NEGATIVE_EMOTIONS = ["sad", "angry", "anxious", "embarrassed", "tired"]

    INTENT_ROMAJI_MAP = {
        "招呼用语": "zhaohu_yongyu",
        "礼貌用语": "limao_yongyu",
        "祝福用语": "zhufu_yongyu",
        "祝贺用语": "zhuhe_yongyu",
        "赞美用语": "zanmei_yongyu",
        "结束用语": "jieshu_yongyu",
        "请求谅解": "qingqiu_liangjie",
        "语气词": "yuqi_ci",
        "肯定(好的)": "kending_haode",
        "肯定(是的)": "kending_shide",
        "肯定(可以)": "kending_keyi",
        "肯定(知道了)": "kending_zhidaole",
        "肯定(嗯嗯)": "kending_enen",
        "肯定(有)": "kending_you",
        "肯定(好了)": "kending_haole",
        "肯定(正确)": "kending_zhengque",
        "否定(不需要)": "fouding_buxuyao",
        "否定(不想要)": "fouding_buxiangyao",
        "否定(不可以)": "fouding_bukeyi",
        "否定(不知道)": "fouding_buzhidao",
        "否定(没时间)": "fouding_meishijian",
        "否定(没兴趣)": "fouding_meixingqu",
        "否定(不方便)": "fouding_bufangbian",
        "否定(不是)": "fouding_bushi",
        "否定(不清楚)": "fouding_buqingchu",
        "否定(不用了)": "fouding_buyongle",
        "否定(取消)": "fouding_quxiao",
        "否定(错误)": "fouding_cuowu",
        "否定答复": "fouding_dafu",
        "疑问(时间)": "yiwen_shijian",
        "疑问(地址)": "yiwen_dizhi",
        "疑问(数值)": "yiwen_shuzhi",
        "疑问(时长)": "yiwen_shichang",
        "查详细信息": "cha_xiangxi_xinxi",
        "查联系方式": "cha_lianxi_fangshi",
        "查自我介绍": "cha_ziwo_jieshao",
        "查优惠政策": "cha_youhui_zhengce",
        "查公司介绍": "cha_gongsi_jieshao",
        "查操作流程": "cha_caozuo_liucheng",
        "查收费方式": "cha_shoufei_fangshi",
        "查物品信息": "cha_wupin_xinxi",
        "号码来源": "haoma_laiyuan",
        "质疑来电号码": "zhiyi_laidian_haoma",
        "问意图": "wen_yitu",
        "实体(地址)": "shiti_dizhi",
        "答时间": "da_shijian",
        "答非所问": "da_feisuowen",
        "请等一等": "qing_deng_yideng",
        "请讲": "qing_jiang",
        "听不清楚": "ting_bu_qingchu",
        "你还在吗": "ni_hai_zai_ma",
        "我在": "wo_zai",
        "未能理解": "weineng_lijie",
        "听我说话": "ting_wo_shuohua",
        "用户正忙": "yonghu_zhengmang",
        "改天再谈": "gaitian_zaitan",
        "时间推迟": "shijian_tuichi",
        "是否机器人": "shifou_jiqiren",
        "要求复述": "yaoqiu_fushu",
        "请讲重点": "qing_jiang_zhongdian",
        "转人工客服": "zhuan_rengong_kefu",
        "投诉警告": "tousu_jinggao",
        "不信任": "buxinren",
        "价格太高": "jiage_taigao",
        "打错电话": "dacuo_dianhua",
        "资金困难": "zijin_kunnan",
        "遭遇不幸": "zaoyu_buxing",
        "骚扰电话": "saorao_dianhua",
        "已完成": "yi_wancheng",
        "会按时处理": "hui_anshi_chuli",
    }

    @staticmethod
    def should_send_sticker(emotion_map: Dict[str, str]) -> bool:
        if not emotion_map:
            return True

        if "serious" in emotion_map:
            return False

        high_negative_rules = [
            ("serious", ["low", "medium", "high", "extreme"]),
            ("sad", ["high", "extreme"]),
            ("angry", ["high", "extreme"]),
            ("anxious", ["extreme"]),
            ("tired", ["extreme"]),
        ]

        for emo, levels in high_negative_rules:
            if emo in emotion_map and emotion_map[emo] in levels:
                return False

        negative_emotions = ["sad", "angry", "anxious", "embarrassed"]
        high_negative_count = sum(
            1
            for emo in negative_emotions
            if emo in emotion_map and emotion_map[emo] in ["high", "extreme"]
        )

        if high_negative_count >= 2:
            return False

        return True

    @staticmethod
    def get_emotion_category(emotion_map: Dict[str, str]) -> str:
        if not emotion_map:
            return "neutral"

        level_weights = {"low": 1, "medium": 2, "high": 3, "extreme": 4}
        positive_score = 0
        negative_score = 0

        for emo, level in emotion_map.items():
            weight = level_weights.get(level, 2)
            if emo in StickerSelector.POSITIVE_EMOTIONS:
                positive_score += weight
            elif emo in StickerSelector.NEGATIVE_EMOTIONS:
                negative_score += weight

        if positive_score > negative_score:
            return "positive"
        elif negative_score > positive_score:
            return "negative"
        return "neutral"

    @staticmethod
    def get_confidence_threshold(emotion_map: Dict[str, str]) -> float:
        category = StickerSelector.get_emotion_category(emotion_map)
        return StickerSelector.CONFIDENCE_THRESHOLDS.get(
            category, StickerSelector.CONFIDENCE_THRESHOLDS["default"]
        )

    @staticmethod
    def predict_intent(text: str) -> Tuple[str, float]:
        predictor = IntentPredictor.get_instance()
        return predictor.predict(text)

    @staticmethod
    def select_sticker(
        text: str,
        sticker_packs: List[str],
        emotion_map: Dict[str, str],
        send_probability: float = 0.4,
        confidence_threshold_positive: float = 0.6,
        confidence_threshold_neutral: float = 0.7,
        confidence_threshold_negative: float = 0.8,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        if not sticker_packs:
            log_entry = unified_logger.info(
                "No sticker packs configured",
                category=LogCategory.BEHAVIOR,
                metadata={"reason": "no_packs"},
            )
            return False, "", log_entry

        sticker_base = Path(__file__).parent.parent.parent.parent / "data" / "stickers"

        available_packs = []
        for pack in sticker_packs:
            pack_path = sticker_base / pack
            if pack_path.exists() and pack_path.is_dir():
                available_packs.append(pack)

        if not available_packs:
            log_entry = unified_logger.warning(
                f"No valid sticker packs found",
                category=LogCategory.BEHAVIOR,
                metadata={
                    "configured_packs": sticker_packs,
                    "reason": "packs_not_found",
                },
            )
            return False, "", log_entry

        if not StickerSelector.should_send_sticker(emotion_map):
            log_entry = unified_logger.info(
                "Sticker blocked by emotion state",
                category=LogCategory.BEHAVIOR,
                metadata={
                    "emotion_map": emotion_map,
                    "reason": "emotion_filter",
                },
            )
            return False, "", log_entry

        probability_roll = random.random()
        if probability_roll >= send_probability:
            log_entry = unified_logger.info(
                "Sticker blocked by probability check",
                category=LogCategory.BEHAVIOR,
                metadata={
                    "send_probability": send_probability,
                    "roll": probability_roll,
                    "reason": "probability_filter",
                },
            )
            return False, "", log_entry

        try:
            intent, confidence = StickerSelector.predict_intent(text)
            predictor = IntentPredictor.get_instance()
            use_bert = predictor._model is not None
        except Exception as e:
            log_entry = unified_logger.error(
                f"Intent prediction failed: {e}",
                category=LogCategory.BEHAVIOR,
                metadata={"text_preview": text[:50], "reason": "prediction_error"},
            )
            return False, "", log_entry

        emotion_category = StickerSelector.get_emotion_category(emotion_map)
        if emotion_category == "positive":
            threshold = confidence_threshold_positive
        elif emotion_category == "negative":
            threshold = confidence_threshold_negative
        else:
            threshold = confidence_threshold_neutral

        log_entry = unified_logger.info(
            f"Intent predicted: {intent}",
            category=LogCategory.BEHAVIOR,
            metadata={
                "intent": intent,
                "confidence": confidence,
                "threshold": threshold,
                "emotion_category": emotion_category,
                "text_preview": text[:50],
                "model_type": "BERT" if use_bert else "fallback_keyword",
            },
        )

        if confidence < threshold:
            log_entry = unified_logger.info(
                f"Confidence too low for sticker",
                category=LogCategory.BEHAVIOR,
                metadata={
                    "intent": intent,
                    "confidence": confidence,
                    "threshold": threshold,
                    "reason": "low_confidence",
                },
            )
            return False, "", log_entry

        romaji = StickerSelector.INTENT_ROMAJI_MAP.get(intent)
        if not romaji:
            log_entry = unified_logger.warning(
                f"No romaji mapping for intent",
                category=LogCategory.BEHAVIOR,
                metadata={
                    "intent": intent,
                    "reason": "no_mapping",
                },
            )
            return False, "", log_entry

        sticker_files = []
        for pack in available_packs:
            intent_dir = sticker_base / pack / romaji
            if intent_dir.exists() and intent_dir.is_dir():
                for file_path in intent_dir.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in [
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".gif",
                        ".webp",
                    ]:
                        rel_path = file_path.relative_to(sticker_base)
                        sticker_files.append(str(rel_path))

        if not sticker_files:
            log_entry = unified_logger.warning(
                f"No sticker files found for intent",
                category=LogCategory.BEHAVIOR,
                metadata={
                    "intent": intent,
                    "romaji": romaji,
                    "available_packs": available_packs,
                    "reason": "no_files",
                },
            )
            return False, "", log_entry

        selected = random.choice(sticker_files)
        log_entry = unified_logger.info(
            f"Sticker selected: {selected}",
            category=LogCategory.BEHAVIOR,
            metadata={
                "intent": intent,
                "confidence": confidence,
                "sticker_path": selected,
                "available_count": len(sticker_files),
                "packs_used": available_packs,
            },
        )
        return True, selected, log_entry

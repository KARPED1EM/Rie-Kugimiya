"""
微信聊天意图识别与表情包选择集成模块

功能：
1. 根据情绪判断是否应该发送表情包
2. 调用意图识别模型预测文本意图
3. 根据置信度和意图选择相应的表情包

作者：Manus AI
日期：2024
"""

from typing import Dict, Tuple
from pathlib import Path
import os

# 导入意图映射模块
try:
    from intent_romaji_mapping import (
        get_sticker_path,
        check_sticker_exists,
        INTENT_ROMAJI_MAP,
    )
except ImportError:
    print("警告：无法导入 intent_romaji_mapping 模块，请确保文件在同一目录下")
    get_sticker_path = None
    check_sticker_exists = None
    INTENT_ROMAJI_MAP = {}


# ============================================================================
# 配置参数
# ============================================================================

# 置信度阈值配置
CONFIDENCE_THRESHOLDS = {
    # 积极情绪：较低阈值（更宽松）
    "positive": 0.6,
    # 中性情绪：标准阈值
    "neutral": 0.7,
    # 负面情绪：较高阈值（更谨慎）
    "negative": 0.8,
    # 默认阈值
    "default": 0.7,
}

# 情绪分类
POSITIVE_EMOTIONS = ["happy", "excited", "playful", "affectionate", "surprised"]
NEUTRAL_EMOTIONS = ["neutral", "confused", "shy", "bored", "caring"]
NEGATIVE_EMOTIONS = ["sad", "angry", "anxious", "embarrassed", "tired"]


# ============================================================================
# 情绪判断规则
# ============================================================================


def should_send_sticker(emotion: Dict[str, str]) -> bool:
    """
    判断是否应该发送表情包（基于情绪）

    规则：
    1. 严肃情绪（任何程度）→ 不发送
    2. 高程度负面情绪 → 不发送
       - sad/angry: high/extreme
       - anxious/tired: extreme
    3. 多重高程度负面情绪（>=2个）→ 不发送
    4. 其他情况 → 可以发送

    Args:
        emotion: 情绪字典，格式为 {"<emotion>": "<low|medium|high|extreme>"}

    Returns:
        True 如果应该发送表情包，否则 False

    Examples:
        >>> should_send_sticker({"happy": "high"})
        True
        >>> should_send_sticker({"serious": "low"})
        False
        >>> should_send_sticker({"sad": "extreme"})
        False
    """
    # 规则1：严肃情绪，任何程度都不发送
    if "serious" in emotion:
        return False

    # 规则2：高程度负面情绪不发送
    high_negative_rules = [
        ("sad", ["high", "extreme"]),
        ("angry", ["high", "extreme"]),
        ("anxious", ["extreme"]),
        ("tired", ["extreme"]),
    ]

    for emo, levels in high_negative_rules:
        if emo in emotion and emotion[emo] in levels:
            return False

    # 规则3：多重高程度负面情绪不发送
    negative_emotions = ["sad", "angry", "anxious", "embarrassed"]
    high_negative_count = sum(
        1
        for emo in negative_emotions
        if emo in emotion and emotion[emo] in ["high", "extreme"]
    )

    if high_negative_count >= 2:
        return False

    # 通过所有检查，可以发送
    return True


def get_emotion_category(emotion: Dict[str, str]) -> str:
    """
    获取情绪的整体类别（用于确定置信度阈值）

    Args:
        emotion: 情绪字典

    Returns:
        "positive", "neutral", 或 "negative"
    """
    # 统计各类情绪的数量和程度
    positive_score = 0
    negative_score = 0

    level_weights = {"low": 1, "medium": 2, "high": 3, "extreme": 4}

    for emo, level in emotion.items():
        weight = level_weights.get(level, 2)

        if emo in POSITIVE_EMOTIONS:
            positive_score += weight
        elif emo in NEGATIVE_EMOTIONS:
            negative_score += weight

    # 判断整体倾向
    if positive_score > negative_score:
        return "positive"
    elif negative_score > positive_score:
        return "negative"
    else:
        return "neutral"


def get_confidence_threshold(emotion: Dict[str, str]) -> float:
    """
    根据情绪获取置信度阈值

    Args:
        emotion: 情绪字典

    Returns:
        置信度阈值（0.0-1.0）
    """
    category = get_emotion_category(emotion)
    return CONFIDENCE_THRESHOLDS.get(category, CONFIDENCE_THRESHOLDS["default"])


# ============================================================================
# 意图识别（占位函数，需要替换为实际模型）
# ============================================================================


def predict_intent(msg: str) -> Tuple[str, float]:
    """
    预测文本的意图和置信度

    注意：这是一个占位函数，实际使用时需要替换为真实的模型预测代码

    Args:
        msg: 输入文本

    Returns:
        (intent, confidence): 意图名称和置信度

    Examples:
        >>> predict_intent("你好呀")
        ("招呼用语", 0.95)
    """
    # TODO: 替换为实际的模型预测代码
    # 例如：
    # from your_model import WeChatIntentPredictor
    # predictor = WeChatIntentPredictor("model_path")
    # results = predictor.predict(msg, top_k=1)
    # return results[0]["intent"], results[0]["confidence"]

    # 临时实现：简单的关键词匹配
    msg_lower = msg.lower()

    if any(word in msg for word in ["你好", "您好", "hi", "hello"]):
        return "招呼用语", 0.95
    elif any(word in msg for word in ["谢谢", "感谢", "多谢"]):
        return "礼貌用语", 0.90
    elif any(word in msg for word in ["好的", "可以", "行", "没问题"]):
        return "肯定(好的)", 0.85
    elif any(word in msg for word in ["不", "不要", "不用", "不需要"]):
        return "否定(不需要)", 0.80
    elif any(word in msg for word in ["什么时候", "几点", "时间"]):
        return "疑问(时间)", 0.75
    elif any(word in msg for word in ["在哪", "地址", "位置"]):
        return "疑问(地址)", 0.75
    else:
        return "未知意图", 0.30


# ============================================================================
# 主入口函数
# ============================================================================


def entry(msg: str, emotion: Dict[str, str]) -> Tuple[bool, str]:
    """
    主入口函数：判断是否发送表情包，并返回表情包路径

    处理流程：
    1. 检查情绪是否适合发送表情包
    2. 调用模型预测文本意图
    3. 检查置信度是否达到阈值
    4. 根据意图选择表情包并返回路径

    Args:
        msg: 需要预测意图的消息内容
        emotion: 情绪字典，格式为 {"<emotion>": "<low|medium|high|extreme>"}
                至少包含一个情绪，数量不定

    Returns:
        (should_send, sticker_path):
            - should_send: bool，是否应该发送表情包
            - sticker_path: str，表情包的相对路径（如果不发送则为空字符串）

    Examples:
        >>> entry("你好呀", {"happy": "high"})
        (True, "stickers/zhaohu_yongyu.png")

        >>> entry("我很难过", {"sad": "extreme"})
        (False, "")

        >>> entry("随便聊聊", {"neutral": "medium"})
        (False, "")  # 置信度不足
    """
    # 步骤1：检查情绪是否适合发送表情包
    if not should_send_sticker(emotion):
        return False, ""

    # 步骤2：预测文本意图
    try:
        intent, confidence = predict_intent(msg)
    except Exception as e:
        print(f"意图预测失败: {e}")
        return False, ""

    # 步骤3：检查置信度是否达到阈值
    threshold = get_confidence_threshold(emotion)
    if confidence < threshold:
        return False, ""

    # 步骤4：根据意图选择表情包
    if get_sticker_path is None:
        print("错误：未加载 intent_romaji_mapping 模块")
        return False, ""

    # 获取表情包路径
    sticker_path = get_sticker_path(intent)

    # 检查表情包文件是否存在
    if sticker_path is None or not check_sticker_exists(intent):
        return False, ""

    # 返回相对路径
    return True, sticker_path


# ============================================================================
# 辅助函数
# ============================================================================


def get_sticker_path_absolute(intent: str) -> str:
    """
    获取表情包的绝对路径

    Args:
        intent: 意图名称

    Returns:
        表情包的绝对路径
    """
    sticker_path = get_sticker_path(intent)
    if sticker_path:
        return str(Path(sticker_path).resolve())
    return ""


def list_available_intents() -> list:
    """
    列出所有可用的意图

    Returns:
        意图名称列表
    """
    return list(INTENT_ROMAJI_MAP.keys())


def test_entry_function():
    """测试入口函数"""
    print("=" * 60)
    print("测试 entry() 函数")
    print("=" * 60)

    # 测试用例
    test_cases = [
        # (msg, emotion, expected_result_description)
        ("你好呀", {"happy": "high"}, "应该发送（积极情绪+高置信度）"),
        ("谢谢你", {"neutral": "medium"}, "应该发送（中性情绪+高置信度）"),
        ("好的没问题", {"playful": "medium"}, "应该发送（积极情绪+高置信度）"),
        ("我很难过", {"sad": "extreme"}, "不应该发送（极端伤心）"),
        ("太生气了", {"angry": "high"}, "不应该发送（高度愤怒）"),
        ("正式会议", {"serious": "low"}, "不应该发送（严肃情绪）"),
        ("随便聊聊", {"neutral": "medium"}, "可能不发送（置信度不足）"),
        ("什么时候", {"confused": "low"}, "应该发送（轻度困惑+高置信度）"),
    ]

    print("\n测试用例：")
    print("-" * 60)

    for i, (msg, emotion, description) in enumerate(test_cases, 1):
        should_send, sticker_path = entry(msg, emotion)

        print(f"\n测试 {i}: {description}")
        print(f'  输入: "{msg}"')
        print(f"  情绪: {emotion}")
        print(f"  结果: {'✓ 发送' if should_send else '✗ 不发送'}")
        if should_send:
            print(f"  表情: {sticker_path}")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


# ============================================================================
# 主程序
# ============================================================================

if __name__ == "__main__":
    # 运行测试
    test_entry_function()

    # 显示配置信息
    print("\n配置信息：")
    print(f"  置信度阈值（积极）: {CONFIDENCE_THRESHOLDS['positive']}")
    print(f"  置信度阈值（中性）: {CONFIDENCE_THRESHOLDS['neutral']}")
    print(f"  置信度阈值（负面）: {CONFIDENCE_THRESHOLDS['negative']}")
    print(f"  置信度阈值（默认）: {CONFIDENCE_THRESHOLDS['default']}")
    print(f"\n  可用意图数量: {len(INTENT_ROMAJI_MAP)}")

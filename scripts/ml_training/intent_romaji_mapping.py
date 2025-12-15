# -*- coding: utf-8 -*-
"""
微信聊天意图到罗马音表情包文件名映射表
自动定位表情包目录，支持任意位置运行
"""

from pathlib import Path

# 获取当前脚本所在目录
SCRIPT_DIR = Path(__file__).parent.resolve()

# 表情包目录（与脚本在同一目录下）
sticker_DIR = SCRIPT_DIR / "stickers"

# 完整的意图到罗马音映射字典
INTENT_ROMAJI_MAP = {
    # 社交礼仪类（8个）
    "招呼用语": "zhaohu_yongyu",
    "礼貌用语": "limao_yongyu",
    "祝福用语": "zhufu_yongyu",
    "祝贺用语": "zhuhe_yongyu",
    "赞美用语": "zanmei_yongyu",
    "结束用语": "jieshu_yongyu",
    "请求谅解": "qingqiu_liangjie",
    "语气词": "yuqi_ci",
    # 肯定确认类（8个）
    "肯定(好的)": "kending_haode",
    "肯定(是的)": "kending_shide",
    "肯定(可以)": "kending_keyi",
    "肯定(知道了)": "kending_zhidaole",
    "肯定(嗯嗯)": "kending_enen",
    "肯定(有)": "kending_you",
    "肯定(好了)": "kending_haole",
    "肯定(正确)": "kending_zhengque",
    # 否定拒绝类（13个）
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
    # 信息查询类（15个）
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
    # 信息回答类（3个）
    "实体(地址)": "shiti_dizhi",
    "答时间": "da_shijian",
    "答非所问": "da_feisuowen",
    # 对话控制类（14个）
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
    # 问题异议类（7个）
    "投诉警告": "tousu_jinggao",
    "不信任": "buxinren",
    "价格太高": "jiage_taigao",
    "打错电话": "dacuo_dianhua",
    "资金困难": "zijin_kunnan",
    "遭遇不幸": "zaoyu_buxing",
    "骚扰电话": "saorao_dianhua",
    # 状态确认类（2个）
    "已完成": "yi_wancheng",
    "会按时处理": "hui_anshi_chuli",
}

# 反向映射：罗马音到中文
ROMAJI_INTENT_MAP = {v: k for k, v in INTENT_ROMAJI_MAP.items()}


def get_sticker_path(intent_chinese, sticker_dir=None):
    """
    根据中文意图获取表情包文件路径

    Args:
        intent_chinese: 中文意图名称，如 "招呼用语"
        sticker_dir: 表情包目录路径，默认为脚本所在目录下的 stickers 文件夹

    Returns:
        表情包文件的 Path 对象
        如果意图不存在，返回 None

    Examples:
        >>> path = get_sticker_path("招呼用语")
        >>> print(path)
        # Windows: C:\\Users\\ASUS\\Desktop\\Rie-Kugimiya\\models\\scripts\\stickers\\zhaohu_yongyu.png
        # Linux: /home/user/scripts/stickers/zhaohu_yongyu.png
    """
    romaji = INTENT_ROMAJI_MAP.get(intent_chinese)
    if not romaji:
        return None

    # 如果没有指定 sticker_dir，使用默认的脚本同目录下的 stickers
    if sticker_dir is None:
        sticker_dir = sticker_DIR
    else:
        sticker_dir = Path(sticker_dir)

    return sticker_dir / f"{romaji}.png"


def get_sticker_path_str(intent_chinese, sticker_dir=None):
    """
    根据中文意图获取表情包文件路径（字符串格式）

    Args:
        intent_chinese: 中文意图名称，如 "招呼用语"
        sticker_dir: 表情包目录路径，默认为脚本所在目录下的 stickers 文件夹

    Returns:
        表情包文件路径的字符串
        如果意图不存在，返回 None

    Examples:
        >>> path = get_sticker_path_str("招呼用语")
        >>> print(path)
        # 返回系统特定的路径字符串
    """
    path = get_sticker_path(intent_chinese, sticker_dir)
    return str(path) if path else None


def check_sticker_exists(intent_chinese, sticker_dir=None):
    """
    检查表情包文件是否存在

    Args:
        intent_chinese: 中文意图名称
        sticker_dir: 表情包目录路径

    Returns:
        True 如果文件存在，否则 False
    """
    path = get_sticker_path(intent_chinese, sticker_dir)
    return path.exists() if path else False


def get_intent_from_filename(filename):
    """
    根据表情包文件名获取中文意图

    Args:
        filename: 文件名，如 "zhaohu_yongyu.png" 或 "zhaohu_yongyu"

    Returns:
        中文意图名称，如 "招呼用语"
        如果文件名不存在，返回 None
    """
    # 去掉 .png 后缀
    romaji = filename.replace(".png", "")
    return ROMAJI_INTENT_MAP.get(romaji)


def list_all_intents():
    """列出所有意图"""
    return list(INTENT_ROMAJI_MAP.keys())


def list_all_romaji():
    """列出所有罗马音文件名"""
    return list(INTENT_ROMAJI_MAP.values())


def get_intents_by_category():
    """按大类分组返回意图"""
    return {
        "社交礼仪": [
            "招呼用语",
            "礼貌用语",
            "祝福用语",
            "祝贺用语",
            "赞美用语",
            "结束用语",
            "请求谅解",
            "语气词",
        ],
        "肯定确认": [
            "肯定(好的)",
            "肯定(是的)",
            "肯定(可以)",
            "肯定(知道了)",
            "肯定(嗯嗯)",
            "肯定(有)",
            "肯定(好了)",
            "肯定(正确)",
        ],
        "否定拒绝": [
            "否定(不需要)",
            "否定(不想要)",
            "否定(不可以)",
            "否定(不知道)",
            "否定(没时间)",
            "否定(没兴趣)",
            "否定(不方便)",
            "否定(不是)",
            "否定(不清楚)",
            "否定(不用了)",
            "否定(取消)",
            "否定(错误)",
            "否定答复",
        ],
        "信息查询": [
            "疑问(时间)",
            "疑问(地址)",
            "疑问(数值)",
            "疑问(时长)",
            "查详细信息",
            "查联系方式",
            "查自我介绍",
            "查优惠政策",
            "查公司介绍",
            "查操作流程",
            "查收费方式",
            "查物品信息",
            "号码来源",
            "质疑来电号码",
            "问意图",
        ],
        "信息回答": ["实体(地址)", "答时间", "答非所问"],
        "对话控制": [
            "请等一等",
            "请讲",
            "听不清楚",
            "你还在吗",
            "我在",
            "未能理解",
            "听我说话",
            "用户正忙",
            "改天再谈",
            "时间推迟",
            "是否机器人",
            "要求复述",
            "请讲重点",
            "转人工客服",
        ],
        "问题异议": [
            "投诉警告",
            "不信任",
            "价格太高",
            "打错电话",
            "资金困难",
            "遭遇不幸",
            "骚扰电话",
        ],
        "状态确认": ["已完成", "会按时处理"],
    }


def get_sticker_dir_info():
    """获取表情包目录信息"""
    return {
        "script_dir": str(SCRIPT_DIR),
        "sticker_dir": str(sticker_DIR),
        "sticker_dir_exists": sticker_DIR.exists(),
        "sticker_count": (
            len(list(sticker_DIR.glob("*.png"))) if sticker_DIR.exists() else 0
        ),
    }


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("意图到表情包映射测试")
    print("=" * 60)

    # 显示目录信息
    info = get_sticker_dir_info()
    print("\n目录信息:")
    print(f"  脚本目录: {info['script_dir']}")
    print(f"  表情包目录: {info['sticker_dir']}")
    print(f"  表情包目录存在: {info['sticker_dir_exists']}")
    print(f"  表情包文件数: {info['sticker_count']}")

    # 测试1：获取表情包路径
    test_intents = ["招呼用语", "肯定(好的)", "否定(不需要)", "疑问(时间)"]
    print("\n测试1：获取表情包路径")
    for intent in test_intents:
        path = get_sticker_path(intent)
        exists = check_sticker_exists(intent)
        status = "✓" if exists else "✗"
        print(f"  {status} {intent} -> {path}")

    # 测试2：从文件名获取意图
    test_files = ["zhaohu_yongyu.png", "kending_haode", "fouding_buxuyao.png"]
    print("\n测试2：从文件名获取意图")
    for filename in test_files:
        intent = get_intent_from_filename(filename)
        print(f"  {filename} -> {intent}")

    # 测试3：统计信息
    print("\n测试3：统计信息")
    print(f"  总意图数: {len(INTENT_ROMAJI_MAP)}")

    categories = get_intents_by_category()
    print("\n  各大类意图数:")
    for category, intents in categories.items():
        print(f"    {category}: {len(intents)}个")

    # 测试4：检查所有表情包是否存在
    print("\n测试4：检查表情包文件")
    if sticker_DIR.exists():
        missing = []
        for intent in INTENT_ROMAJI_MAP.keys():
            if not check_sticker_exists(intent):
                missing.append(intent)

        if missing:
            print(f"  ⚠ 缺失 {len(missing)} 个表情包:")
            for intent in missing[:5]:  # 只显示前5个
                print(f"    - {intent}")
            if len(missing) > 5:
                print(f"    ... 还有 {len(missing) - 5} 个")
        else:
            print(f"  ✓ 所有70个表情包文件都存在！")
    else:
        print(f"  ✗ 表情包目录不存在: {sticker_DIR}")
        print(f"  请确保 stickers 文件夹与脚本在同一目录下")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

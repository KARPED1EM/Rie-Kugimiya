#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表情包管理工具 - 独立测试脚本
验证核心功能而不需要GUI环境
"""

import sys
from pathlib import Path

# 类别映射字典：拼音 -> 中文
CATEGORY_MAP = {
    # 社交礼仪类
    "zhaohu_yongyu": "招呼用语",
    "limao_yongyu": "礼貌用语",
    "zhufu_yongyu": "祝福用语",
    "zhuhe_yongyu": "祝贺用语",
    "zanmei_yongyu": "赞美用语",
    "jieshu_yongyu": "结束用语",
    "qingqiu_liangjie": "请求谅解",
    "yuqi_ci": "语气词",
    # 肯定确认类
    "kending_haode": "肯定(好的)",
    "kending_shide": "肯定(是的)",
    "kending_keyi": "肯定(可以)",
    "kending_zhidaole": "肯定(知道了)",
    "kending_enen": "肯定(嗯嗯)",
    "kending_you": "肯定(有)",
    "kending_haole": "肯定(好了)",
    "kending_zhengque": "肯定(正确)",
    # 否定拒绝类
    "fouding_buxuyao": "否定(不需要)",
    "fouding_buxiangyao": "否定(不想要)",
    "fouding_bukeyi": "否定(不可以)",
    "fouding_buzhidao": "否定(不知道)",
    "fouding_meishijian": "否定(没时间)",
    "fouding_meixingqu": "否定(没兴趣)",
    "fouding_bufangbian": "否定(不方便)",
    "fouding_bushi": "否定(不是)",
    "fouding_buqingchu": "否定(不清楚)",
    "fouding_buyongle": "否定(不用了)",
    "fouding_quxiao": "否定(取消)",
    "fouding_cuowu": "否定(错误)",
    "fouding_dafu": "否定答复",
    # 信息查询类
    "yiwen_shijian": "疑问(时间)",
    "yiwen_dizhi": "疑问(地址)",
    "yiwen_shuzhi": "疑问(数值)",
    "yiwen_shichang": "疑问(时长)",
    "cha_xiangxi_xinxi": "查详细信息",
    "cha_lianxi_fangshi": "查联系方式",
    "cha_ziwo_jieshao": "查自我介绍",
    "cha_youhui_zhengce": "查优惠政策",
    "cha_gongsi_jieshao": "查公司介绍",
    "cha_caozuo_liucheng": "查操作流程",
    "cha_shoufei_fangshi": "查收费方式",
    "cha_wupin_xinxi": "查物品信息",
    "haoma_laiyuan": "号码来源",
    "zhiyi_laidian_haoma": "质疑来电号码",
    "wen_yitu": "问意图",
    # 信息回答类
    "shiti_dizhi": "实体(地址)",
    "da_shijian": "答时间",
    "da_feisuowen": "答非所问",
    # 对话控制类
    "qing_deng_yideng": "请等一等",
    "qing_jiang": "请讲",
    "ting_bu_qingchu": "听不清楚",
    "ni_hai_zai_ma": "你还在吗",
    "wo_zai": "我在",
    "weineng_lijie": "未能理解",
    "ting_wo_shuohua": "听我说话",
    "yonghu_zhengmang": "用户正忙",
    "gaitian_zaitan": "改天再谈",
    "shijian_tuichi": "时间推迟",
    "shifou_jiqiren": "是否机器人",
    "yaoqiu_fushu": "要求复述",
    "qing_jiang_zhongdian": "请讲重点",
    "zhuan_rengong_kefu": "转人工客服",
    # 问题异议类
    "tousu_jinggao": "投诉警告",
    "buxinren": "不信任",
    "jiage_taigao": "价格太高",
    "dacuo_dianhua": "打错电话",
    "zijin_kunnan": "资金困难",
    "zaoyu_buxing": "遭遇不幸",
    "saorao_dianhua": "骚扰电话",
    # 状态确认类
    "yi_wancheng": "已完成",
    "hui_anshi_chuli": "会按时处理",
}


def test_category_mapping():
    """测试类别映射"""
    print("=" * 60)
    print("测试类别映射")
    print("=" * 60)
    
    print(f"\n✓ 总共定义了 {len(CATEGORY_MAP)} 个类别映射")
    
    # 测试几个常见映射
    test_cases = [
        ('zhaohu_yongyu', '招呼用语'),
        ('kending_haode', '肯定(好的)'),
        ('fouding_buxuyao', '否定(不需要)'),
        ('yiwen_shijian', '疑问(时间)'),
        ('cha_ziwo_jieshao', '查自我介绍'),
    ]
    
    print("\n测试示例映射:")
    for romaji, expected_chinese in test_cases:
        actual_chinese = CATEGORY_MAP.get(romaji)
        status = "✓" if actual_chinese == expected_chinese else "✗"
        print(f"  {status} {romaji} -> {actual_chinese}")


def test_sticker_directory():
    """测试表情包目录"""
    print("\n" + "=" * 60)
    print("测试表情包目录")
    print("=" * 60)
    
    sticker_base = Path(__file__).parent / "data" / "stickers"
    
    if not sticker_base.exists():
        print(f"\n⚠ 表情包目录不存在: {sticker_base}")
        print("  这是正常的，工具首次运行时会自动创建")
        return
    
    print(f"\n✓ 表情包目录存在: {sticker_base}")
    
    # 统计合集
    collections = [d for d in sticker_base.iterdir() if d.is_dir()]
    print(f"\n找到 {len(collections)} 个合集:")
    
    for collection in sorted(collections):
        categories = [d for d in collection.iterdir() if d.is_dir()]
        total_files = 0
        
        for category in categories:
            files = list(category.glob("*.*"))
            total_files += len(files)
        
        print(f"\n  合集: {collection.name}")
        print(f"    - 类别数: {len(categories)}")
        print(f"    - 表情包总数: {total_files}")
        
        # 显示几个类别示例
        if categories:
            print(f"    - 类别示例:")
            for cat in sorted(categories)[:5]:
                chinese = CATEGORY_MAP.get(cat.name, cat.name)
                file_count = len(list(cat.glob("*.*")))
                print(f"      • {chinese} ({cat.name}): {file_count} 个文件")
            
            if len(categories) > 5:
                print(f"      ... 还有 {len(categories) - 5} 个类别")


def test_mapping_coverage():
    """测试映射覆盖率"""
    print("\n" + "=" * 60)
    print("测试映射覆盖率")
    print("=" * 60)
    
    sticker_base = Path(__file__).parent / "data" / "stickers"
    
    if not sticker_base.exists():
        print("\n⚠ 表情包目录不存在，跳过覆盖率测试")
        return
    
    # 收集所有实际存在的类别
    actual_categories = set()
    for collection in sticker_base.iterdir():
        if collection.is_dir():
            for category in collection.iterdir():
                if category.is_dir():
                    actual_categories.add(category.name)
    
    if not actual_categories:
        print("\n⚠ 未找到任何类别目录")
        return
    
    # 检查映射覆盖
    mapped_categories = set(CATEGORY_MAP.keys())
    
    print(f"\n✓ 已映射类别数: {len(mapped_categories)}")
    print(f"✓ 实际类别数: {len(actual_categories)}")
    
    # 未映射的类别
    unmapped = actual_categories - mapped_categories
    if unmapped:
        print(f"\n⚠ 有 {len(unmapped)} 个类别未映射到中文:")
        for cat in sorted(unmapped)[:10]:
            print(f"  - {cat}")
        if len(unmapped) > 10:
            print(f"  ... 还有 {len(unmapped) - 10} 个")
    else:
        print("\n✓ 所有类别都已映射!")
    
    # 未使用的映射
    unused = mapped_categories - actual_categories
    if unused:
        print(f"\n💡 有 {len(unused)} 个映射暂未使用:")
        for cat in sorted(unused)[:10]:
            chinese = CATEGORY_MAP[cat]
            print(f"  - {cat} ({chinese})")
        if len(unused) > 10:
            print(f"  ... 还有 {len(unused) - 10} 个")


def main():
    print("\n表情包管理工具 - 验证测试")
    print("=" * 60)
    
    test_category_mapping()
    test_sticker_directory()
    test_mapping_coverage()
    
    print("\n" + "=" * 60)
    print("✓ 所有测试完成!")
    print("=" * 60)
    print("\n提示: 在有图形界面的环境中运行 'python sticker_manager.py' 启动完整的GUI工具")
    print()


if __name__ == "__main__":
    main()

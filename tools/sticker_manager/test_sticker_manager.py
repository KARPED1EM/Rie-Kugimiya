#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表情包管理工具 - 独立测试脚本
验证核心功能而不需要GUI环境
"""

import sys
from pathlib import Path

# 导入类别映射
from sticker_categories import CATEGORY_MAP


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
    
    # 使用与主程序相同的路径逻辑
    sticker_base = Path(__file__).parent.parent.parent / "data" / "stickers"
    
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
    
    sticker_base = Path(__file__).parent.parent.parent / "data" / "stickers"
    
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

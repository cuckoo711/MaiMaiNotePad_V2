#!/usr/bin/env python
"""
翻译模型重构 - 集成测试脚本

测试前后端集成是否正常工作
"""

import os
import sys
import django

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()

from mainotebook.system.models import Translation
from rest_framework.test import APIClient


def test_translation_data():
    """测试翻译数据是否已迁移"""
    print("=" * 60)
    print("测试 1: 检查翻译数据")
    print("=" * 60)
    
    total_count = Translation.objects.count()
    blocks_count = Translation.objects.filter(
        translation_type='toml_visualizer_blocks'
    ).count()
    tokens_count = Translation.objects.filter(
        translation_type='toml_visualizer_tokens'
    ).count()
    
    print(f"✓ 翻译记录总数: {total_count}")
    print(f"✓ toml_visualizer_blocks: {blocks_count}")
    print(f"✓ toml_visualizer_tokens: {tokens_count}")
    
    if total_count == 0:
        print("✗ 错误: 没有翻译数据！")
        return False
    
    print("✓ 翻译数据检查通过\n")
    return True


def test_translation_api():
    """测试翻译 API 是否正常工作"""
    print("=" * 60)
    print("测试 2: 检查翻译 API")
    print("=" * 60)
    
    client = APIClient()
    
    # 测试列表接口
    print("测试列表接口...")
    response = client.get('/api/system/translation/')
    if response.status_code != 200:
        print(f"✗ 列表接口失败: {response.status_code}")
        return False
    print(f"✓ 列表接口正常 (状态码: {response.status_code})")
    
    # 测试按类型查询 - blocks
    print("\n测试按类型查询 (blocks)...")
    response = client.get(
        '/api/system/translation/get_by_type/?translation_type=toml_visualizer_blocks'
    )
    if response.status_code != 200:
        print(f"✗ 按类型查询失败: {response.status_code}")
        return False
    
    blocks_data = response.data
    print(f"✓ 返回 {len(blocks_data)} 条 blocks 翻译")
    if len(blocks_data) > 0:
        sample = blocks_data[0]
        print(f"  示例: {sample['source_text']} -> {sample['translated_text']}")
    
    # 测试按类型查询 - tokens
    print("\n测试按类型查询 (tokens)...")
    response = client.get(
        '/api/system/translation/get_by_type/?translation_type=toml_visualizer_tokens'
    )
    if response.status_code != 200:
        print(f"✗ 按类型查询失败: {response.status_code}")
        return False
    
    tokens_data = response.data
    print(f"✓ 返回 {len(tokens_data)} 条 tokens 翻译")
    if len(tokens_data) > 0:
        sample = tokens_data[0]
        print(f"  示例: {sample['source_text']} -> {sample['translated_text']}")
    
    print("\n✓ API 接口检查通过\n")
    return True


def test_translation_sorting():
    """测试翻译数据排序"""
    print("=" * 60)
    print("测试 3: 检查翻译数据排序")
    print("=" * 60)
    
    client = APIClient()
    response = client.get(
        '/api/system/translation/get_by_type/?translation_type=toml_visualizer_blocks'
    )
    
    if response.status_code != 200:
        print("✗ 无法获取数据")
        return False
    
    data = response.data
    if len(data) < 2:
        print("✓ 数据量不足，跳过排序测试")
        return True
    
    # 检查是否按 sort 字段排序
    is_sorted = all(
        data[i]['sort'] <= data[i + 1]['sort']
        for i in range(len(data) - 1)
    )
    
    if is_sorted:
        print("✓ 数据按 sort 字段正确排序")
        print(f"  第一条: sort={data[0]['sort']}, {data[0]['source_text']}")
        print(f"  最后一条: sort={data[-1]['sort']}, {data[-1]['source_text']}")
    else:
        print("✗ 数据排序不正确")
        return False
    
    print("✓ 排序检查通过\n")
    return True


def test_migration_idempotency():
    """测试迁移脚本的幂等性"""
    print("=" * 60)
    print("测试 4: 检查迁移脚本幂等性")
    print("=" * 60)
    
    from django.core.management import call_command
    from io import StringIO
    
    # 记录当前记录数
    before_count = Translation.objects.count()
    print(f"迁移前记录数: {before_count}")
    
    # 执行迁移（模拟运行）
    print("执行迁移脚本（模拟运行）...")
    out = StringIO()
    call_command('migrate_translation', '--dry-run', stdout=out)
    output = out.getvalue()
    
    # 检查输出
    if '跳过' in output and '成功: 0' in output:
        print("✓ 迁移脚本正确跳过已存在的记录")
    else:
        print("✗ 迁移脚本可能会创建重复记录")
        return False
    
    # 确认记录数未变化
    after_count = Translation.objects.count()
    if before_count == after_count:
        print(f"✓ 记录数保持不变: {after_count}")
    else:
        print(f"✗ 记录数发生变化: {before_count} -> {after_count}")
        return False
    
    print("✓ 幂等性检查通过\n")
    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("翻译模型重构 - 集成测试")
    print("=" * 60 + "\n")
    
    tests = [
        ("翻译数据检查", test_translation_data),
        ("API 接口检查", test_translation_api),
        ("排序功能检查", test_translation_sorting),
        ("幂等性检查", test_migration_idempotency),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ 测试失败: {e}")
            results.append((name, False))
    
    # 输出总结
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！前后端集成正常。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查问题。")
        return 1


if __name__ == '__main__':
    sys.exit(main())

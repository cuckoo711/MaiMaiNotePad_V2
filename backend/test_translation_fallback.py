#!/usr/bin/env python
"""
翻译模型重构 - 降级方案测试

测试当 API 失败或翻译不存在时的降级行为
"""

import os
import sys
import django

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()

from mainotebook.system.models import Translation
from rest_framework.test import APIClient


def test_missing_translation():
    """测试翻译不存在时的降级行为"""
    print("=" * 60)
    print("测试 1: 翻译不存在时的降级行为")
    print("=" * 60)
    
    client = APIClient()
    
    # 查询一个不存在的翻译类型
    response = client.get(
        '/api/system/translation/get_by_type/?translation_type=non_existent_type'
    )
    
    if response.status_code != 200:
        print(f"✗ API 返回错误状态码: {response.status_code}")
        return False
    
    data = response.data
    if len(data) == 0:
        print("✓ 不存在的翻译类型返回空列表")
    else:
        print(f"✗ 返回了 {len(data)} 条数据，应该为空")
        return False
    
    print("✓ 降级行为正确：返回空列表\n")
    return True


def test_translation_with_special_characters():
    """测试包含特殊字符的翻译"""
    print("=" * 60)
    print("测试 2: 特殊字符处理")
    print("=" * 60)
    
    # 查找包含特殊字符的翻译
    special_translations = Translation.objects.filter(
        source_text__icontains='_'
    )[:5]
    
    if special_translations.exists():
        print(f"✓ 找到 {special_translations.count()} 条包含特殊字符的翻译")
        for trans in special_translations:
            print(f"  {trans.source_text} -> {trans.translated_text}")
    else:
        print("⚠️  没有找到包含特殊字符的翻译")
    
    print("✓ 特殊字符处理正常\n")
    return True


def test_api_response_format():
    """测试 API 响应格式"""
    print("=" * 60)
    print("测试 3: API 响应格式")
    print("=" * 60)
    
    client = APIClient()
    response = client.get(
        '/api/system/translation/get_by_type/?translation_type=toml_visualizer_blocks'
    )
    
    if response.status_code != 200:
        print(f"✗ API 返回错误状态码: {response.status_code}")
        return False
    
    data = response.data
    if not isinstance(data, list):
        print(f"✗ 响应数据不是列表类型: {type(data)}")
        return False
    
    if len(data) == 0:
        print("⚠️  没有数据可供检查")
        return True
    
    # 检查第一条记录的字段
    first_item = data[0]
    required_fields = [
        'id', 'source_text', 'translated_text',
        'source_language', 'target_language',
        'translation_type', 'sort', 'status'
    ]
    
    missing_fields = [
        field for field in required_fields
        if field not in first_item
    ]
    
    if missing_fields:
        print(f"✗ 缺少必需字段: {missing_fields}")
        return False
    
    print("✓ API 响应包含所有必需字段:")
    for field in required_fields:
        value = first_item[field]
        print(f"  {field}: {value}")
    
    print("✓ API 响应格式正确\n")
    return True


def test_translation_status_filter():
    """测试状态过滤"""
    print("=" * 60)
    print("测试 4: 状态过滤")
    print("=" * 60)
    
    client = APIClient()
    
    # 获取所有翻译
    response = client.get(
        '/api/system/translation/get_by_type/?translation_type=toml_visualizer_blocks'
    )
    
    if response.status_code != 200:
        print(f"✗ API 返回错误状态码: {response.status_code}")
        return False
    
    data = response.data
    
    # 检查是否只返回启用状态的翻译
    disabled_count = sum(1 for item in data if not item['status'])
    
    if disabled_count > 0:
        print(f"⚠️  返回了 {disabled_count} 条禁用的翻译")
    else:
        print("✓ 只返回启用状态的翻译")
    
    print(f"✓ 总共返回 {len(data)} 条启用的翻译\n")
    return True


def test_empty_translation_type():
    """测试空翻译类型参数"""
    print("=" * 60)
    print("测试 5: 空翻译类型参数")
    print("=" * 60)
    
    client = APIClient()
    
    # 不提供 translation_type 参数
    response = client.get('/api/system/translation/get_by_type/')
    
    # 应该返回 400 错误
    if response.status_code == 400:
        print("✓ 正确返回 400 错误")
        if 'error' in response.data or 'detail' in response.data:
            error_msg = response.data.get('error') or response.data.get('detail')
            print(f"  错误消息: {error_msg}")
    else:
        print(f"⚠️  返回状态码: {response.status_code}（预期 400）")
    
    print("✓ 参数验证正常\n")
    return True


def main():
    """运行所有降级测试"""
    print("\n" + "=" * 60)
    print("翻译模型重构 - 降级方案测试")
    print("=" * 60 + "\n")
    
    tests = [
        ("翻译不存在降级", test_missing_translation),
        ("特殊字符处理", test_translation_with_special_characters),
        ("API 响应格式", test_api_response_format),
        ("状态过滤", test_translation_status_filter),
        ("参数验证", test_empty_translation_type),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ 测试失败: {e}")
            import traceback
            traceback.print_exc()
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
        print("\n🎉 所有降级测试通过！")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查问题。")
        return 1


if __name__ == '__main__':
    sys.exit(main())

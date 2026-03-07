#!/usr/bin/env python
"""系统账号保护机制测试脚本

测试 ai_reviewer 系统账号的保护机制：
1. 验证账号存在且 user_type=2
2. 验证 is_system_account() 方法
3. 验证 can_be_moderated() 方法
4. 验证 can_be_deleted() 方法
5. 验证无法登录（is_active=False, password="!"）
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()

from mainotebook.system.models import Users


def test_system_account_protection():
    """测试系统账号保护机制"""
    
    print("=" * 60)
    print("系统账号保护机制测试")
    print("=" * 60)
    
    # 1. 查找 ai_reviewer 账号
    print("\n[测试 1] 查找 ai_reviewer 账号...")
    try:
        ai_reviewer = Users.objects.get(username='ai_reviewer')
        print(f"✓ 找到账号: {ai_reviewer.username}")
        print(f"  - ID: {ai_reviewer.id}")
        print(f"  - 名称: {ai_reviewer.name}")
        print(f"  - 用户类型: {ai_reviewer.user_type} ({ai_reviewer.get_user_type_display()})")
        print(f"  - 是否激活: {ai_reviewer.is_active}")
        print(f"  - 密码: {ai_reviewer.password[:20]}...")
    except Users.DoesNotExist:
        print("✗ 未找到 ai_reviewer 账号")
        print("  请先运行: python manage.py init")
        return False
    
    # 2. 验证 user_type=2
    print("\n[测试 2] 验证 user_type=2...")
    if ai_reviewer.user_type == 2:
        print("✓ user_type 正确设置为 2（系统账号）")
    else:
        print(f"✗ user_type 错误: {ai_reviewer.user_type}，应该为 2")
        return False
    
    # 3. 验证 is_system_account() 方法
    print("\n[测试 3] 验证 is_system_account() 方法...")
    if ai_reviewer.is_system_account():
        print("✓ is_system_account() 返回 True")
    else:
        print("✗ is_system_account() 返回 False，应该返回 True")
        return False
    
    # 4. 验证 can_be_moderated() 方法
    print("\n[测试 4] 验证 can_be_moderated() 方法...")
    if not ai_reviewer.can_be_moderated():
        print("✓ can_be_moderated() 返回 False（系统账号不能被处罚）")
    else:
        print("✗ can_be_moderated() 返回 True，应该返回 False")
        return False
    
    # 5. 验证 can_be_deleted() 方法
    print("\n[测试 5] 验证 can_be_deleted() 方法...")
    if not ai_reviewer.can_be_deleted():
        print("✓ can_be_deleted() 返回 False（系统账号不能被删除）")
    else:
        print("✗ can_be_deleted() 返回 True，应该返回 False")
        return False
    
    # 6. 验证无法登录
    print("\n[测试 6] 验证无法登录...")
    if not ai_reviewer.is_active:
        print("✓ is_active=False（账号已禁用）")
    else:
        print("✗ is_active=True，应该为 False")
        return False
    
    if ai_reviewer.password == "!":
        print("✓ password='!'（无效密码，无法登录）")
    else:
        print(f"✗ password='{ai_reviewer.password[:20]}...'，应该为 '!'")
        return False
    
    # 7. 对比普通用户
    print("\n[测试 7] 对比普通用户...")
    try:
        normal_user = Users.objects.filter(user_type__in=[0, 1]).first()
        if normal_user:
            print(f"  普通用户: {normal_user.username}")
            print(f"  - is_system_account(): {normal_user.is_system_account()}")
            print(f"  - can_be_moderated(): {normal_user.can_be_moderated()}")
            print(f"  - can_be_deleted(): {normal_user.can_be_deleted()}")
            
            if not normal_user.is_system_account() and \
               normal_user.can_be_moderated() and \
               normal_user.can_be_deleted():
                print("✓ 普通用户的方法返回值正确")
            else:
                print("✗ 普通用户的方法返回值不正确")
                return False
    except Exception as e:
        print(f"  警告: 无法测试普通用户 - {e}")
    
    print("\n" + "=" * 60)
    print("✓ 所有测试通过！系统账号保护机制正常工作")
    print("=" * 60)
    return True


if __name__ == '__main__':
    success = test_system_account_protection()
    sys.exit(0 if success else 1)

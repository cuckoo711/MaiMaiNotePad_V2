#!/usr/bin/env python
"""修复 ai_reviewer 系统账号

将现有的 ai_reviewer 账号更新为系统账号类型：
- user_type: 0 -> 2
- is_active: True -> False
- password: (当前密码) -> "!"
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()

from mainotebook.system.models import Users


def fix_ai_reviewer_account():
    """修复 ai_reviewer 账号"""
    
    print("=" * 60)
    print("修复 ai_reviewer 系统账号")
    print("=" * 60)
    
    try:
        ai_reviewer = Users.objects.get(username='ai_reviewer')
        print(f"\n找到账号: {ai_reviewer.username}")
        print(f"当前状态:")
        print(f"  - user_type: {ai_reviewer.user_type} ({ai_reviewer.get_user_type_display()})")
        print(f"  - is_active: {ai_reviewer.is_active}")
        print(f"  - password: {ai_reviewer.password[:20]}...")
        
        # 更新账号
        print(f"\n正在更新...")
        ai_reviewer.user_type = 2
        ai_reviewer.is_active = False
        ai_reviewer.password = "!"
        ai_reviewer.save()
        
        print(f"\n更新后状态:")
        print(f"  - user_type: {ai_reviewer.user_type} ({ai_reviewer.get_user_type_display()})")
        print(f"  - is_active: {ai_reviewer.is_active}")
        print(f"  - password: {ai_reviewer.password}")
        
        print("\n" + "=" * 60)
        print("✓ ai_reviewer 账号已成功更新为系统账号")
        print("=" * 60)
        return True
        
    except Users.DoesNotExist:
        print("\n✗ 未找到 ai_reviewer 账号")
        print("  账号将在下次运行 python manage.py init 时创建")
        return False
    except Exception as e:
        print(f"\n✗ 更新失败: {e}")
        return False


if __name__ == '__main__':
    success = fix_ai_reviewer_account()
    sys.exit(0 if success else 1)

#!/usr/bin/env python
"""
修复缺失的菜单按钮

为"禁言列表"和"封禁列表"菜单创建缺失的MenuButton
"""
import os
import sys
import django

# 设置Django环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()

from mainotebook.system.models import Menu, MenuButton

def fix_missing_buttons():
    """修复缺失的菜单按钮"""
    
    print("=" * 80)
    print("修复缺失的菜单按钮")
    print("=" * 80)
    
    # 1. 获取"禁言列表"菜单
    print("\n【1】修复禁言列表菜单按钮...")
    mute_menu = Menu.objects.filter(name="禁言列表", web_path="/moderation/mute-list").first()
    if not mute_menu:
        print("  ✗ 未找到禁言列表菜单")
        return
    
    print(f"  找到菜单: {mute_menu.name} (ID: {mute_menu.id})")
    
    mute_buttons = [
        {"name": "查询", "value": "mute:Search", "api": "/api/content/moderation/mute-list/", "method": 0},
        {"name": "解除禁言", "value": "mute:Unmute", "api": "/api/content/moderation/unmute/", "method": 1},
        {"name": "修改时长", "value": "mute:ModifyDuration", "api": "/api/content/moderation/modify-duration/", "method": 2},
        {"name": "批量解除", "value": "mute:BatchUnmute", "api": "/api/content/moderation/batch-unmute/", "method": 1},
        {"name": "查看详情", "value": "mute:Detail", "api": "/api/content/moderation/logs/", "method": 0},
        {"name": "导出", "value": "mute:Export", "api": "/api/content/moderation/export/", "method": 0},
    ]
    
    for btn_data in mute_buttons:
        btn, created = MenuButton.objects.get_or_create(
            menu=mute_menu,
            value=btn_data['value'],
            defaults={
                'name': btn_data['name'],
                'api': btn_data['api'],
                'method': btn_data['method']
            }
        )
        if created:
            print(f"  ✓ 创建按钮: {btn.name} ({btn.value})")
        else:
            print(f"  - 按钮已存在: {btn.name} ({btn.value})")
    
    # 2. 获取"封禁列表"菜单
    print("\n【2】修复封禁列表菜单按钮...")
    ban_menu = Menu.objects.filter(name="封禁列表", web_path="/moderation/ban-list").first()
    if not ban_menu:
        print("  ✗ 未找到封禁列表菜单")
        return
    
    print(f"  找到菜单: {ban_menu.name} (ID: {ban_menu.id})")
    
    ban_buttons = [
        {"name": "查询", "value": "ban:Search", "api": "/api/content/moderation/ban-list/", "method": 0},
        {"name": "解除封禁", "value": "ban:Unban", "api": "/api/content/moderation/unban/", "method": 1},
        {"name": "修改时长", "value": "ban:ModifyDuration", "api": "/api/content/moderation/modify-duration/", "method": 2},
        {"name": "批量解除", "value": "ban:BatchUnban", "api": "/api/content/moderation/batch-unban/", "method": 1},
        {"name": "查看详情", "value": "ban:Detail", "api": "/api/content/moderation/logs/", "method": 0},
        {"name": "导出", "value": "ban:Export", "api": "/api/content/moderation/export/", "method": 0},
    ]
    
    for btn_data in ban_buttons:
        btn, created = MenuButton.objects.get_or_create(
            menu=ban_menu,
            value=btn_data['value'],
            defaults={
                'name': btn_data['name'],
                'api': btn_data['api'],
                'method': btn_data['method']
            }
        )
        if created:
            print(f"  ✓ 创建按钮: {btn.name} ({btn.value})")
        else:
            print(f"  - 按钮已存在: {btn.name} ({btn.value})")
    
    print("\n" + "=" * 80)
    print("修复完成！")
    print("=" * 80)
    print("\n现在可以运行以下命令重新初始化权限：")
    print("  python manage.py init")

if __name__ == '__main__':
    try:
        fix_missing_buttons()
    except Exception as e:
        print(f"修复失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

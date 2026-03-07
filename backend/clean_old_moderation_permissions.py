#!/usr/bin/env python
"""
清理旧的禁言封禁权限和菜单记录

这个脚本用于清理数据库中旧的菜单和权限记录，
为新的菜单结构让路。
"""
import os
import sys
import django

# 设置Django环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()

from mainotebook.system.models import Menu, MenuButton, RoleMenuButtonPermission

def clean_old_records():
    """清理旧的菜单和权限记录"""
    
    print("开始清理旧的菜单和权限记录...")
    
    # 1. 先删除所有相关的角色菜单按钮权限
    print("\n第1步：清理角色菜单按钮权限...")
    old_permission_values = [
        'mute:Create', 'mute:Search', 'mute:Unmute', 'mute:ModifyDuration', 
        'mute:BatchMute', 'mute:BatchUnmute', 'mute:Detail', 'mute:Export',
        'ban:Create', 'ban:Search', 'ban:Unban', 'ban:ModifyDuration',
        'ban:BatchBan', 'ban:BatchUnban', 'ban:Detail', 'ban:Export',
        'autoMute:Search', 'autoMute:Unmute', 'autoMute:ModifyDuration',
        'autoMute:Detail', 'autoMute:Export',
    ]
    
    for perm_value in old_permission_values:
        deleted = RoleMenuButtonPermission.objects.filter(
            menu_button__value=perm_value
        ).delete()
        if deleted[0] > 0:
            print(f"  删除权限关联: {perm_value} ({deleted[0]}条)")
    
    # 2. 删除旧的菜单按钮
    print("\n第2步：清理菜单按钮...")
    for perm_value in old_permission_values:
        deleted = MenuButton.objects.filter(value=perm_value).delete()
        if deleted[0] > 0:
            print(f"  删除菜单按钮: {perm_value} ({deleted[0]}条)")
    
    # 3. 删除旧的菜单项
    print("\n第3步：清理旧菜单...")
    old_menus = [
        {'name': '禁言管理', 'web_path': '/moderation/mute-list'},
        {'name': '封禁管理', 'web_path': '/moderation/ban-list'},
        {'name': 'AI自动禁言', 'web_path': '/moderation/auto-mute-list'},
    ]
    
    for menu_info in old_menus:
        deleted = Menu.objects.filter(
            name=menu_info['name'],
            web_path=menu_info['web_path']
        ).delete()
        if deleted[0] > 0:
            print(f"  删除旧菜单: {menu_info['name']} ({menu_info['web_path']}) ({deleted[0]}条)")
    
    print("\n清理完成！")
    print("\n现在可以运行以下命令重新初始化：")
    print("  python manage.py init")

if __name__ == '__main__':
    try:
        clean_old_records()
    except Exception as e:
        print(f"清理失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

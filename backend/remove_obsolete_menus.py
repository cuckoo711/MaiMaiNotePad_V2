#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""删除过时的菜单

删除以下不再使用的菜单：
- 禁言列表 (/moderation/mute-list)
- 封禁列表 (/moderation/ban-list)
- AI自动禁言 (/moderation/auto-mute-list)

这些功能已整合到用户管理中，独立的列表页面不再需要。
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()

from mainotebook.system.models import Menu, MenuButton, RoleMenuPermission, RoleMenuButtonPermission


def remove_obsolete_menus():
    """删除过时的菜单及其相关数据"""
    
    print("=" * 80)
    print("删除过时的菜单")
    print("=" * 80)
    
    # 要删除的菜单列表
    obsolete_menus = [
        {'name': '禁言列表', 'web_path': '/moderation/mute-list'},
        {'name': '封禁列表', 'web_path': '/moderation/ban-list'},
        {'name': 'AI自动禁言', 'web_path': '/moderation/auto-mute-list'},
    ]
    
    total_deleted = {
        'menus': 0,
        'buttons': 0,
        'role_menu_permissions': 0,
        'role_button_permissions': 0
    }
    
    for menu_info in obsolete_menus:
        print(f"\n处理菜单: {menu_info['name']} ({menu_info['web_path']})")
        
        # 查找菜单
        menu = Menu.objects.filter(
            name=menu_info['name'],
            web_path=menu_info['web_path']
        ).first()
        
        if not menu:
            print(f"  ✓ 菜单不存在，跳过")
            continue
        
        print(f"  找到菜单 ID: {menu.id}")
        
        # 1. 删除角色菜单按钮权限
        button_permissions = RoleMenuButtonPermission.objects.filter(
            menu_button__menu=menu
        )
        button_perm_count = button_permissions.count()
        if button_perm_count > 0:
            button_permissions.delete()
            print(f"  ✓ 删除 {button_perm_count} 条角色菜单按钮权限")
            total_deleted['role_button_permissions'] += button_perm_count
        
        # 2. 删除角色菜单权限
        menu_permissions = RoleMenuPermission.objects.filter(menu=menu)
        menu_perm_count = menu_permissions.count()
        if menu_perm_count > 0:
            menu_permissions.delete()
            print(f"  ✓ 删除 {menu_perm_count} 条角色菜单权限")
            total_deleted['role_menu_permissions'] += menu_perm_count
        
        # 3. 删除菜单按钮
        buttons = MenuButton.objects.filter(menu=menu)
        button_count = buttons.count()
        if button_count > 0:
            buttons.delete()
            print(f"  ✓ 删除 {button_count} 个菜单按钮")
            total_deleted['buttons'] += button_count
        
        # 4. 删除菜单
        menu.delete()
        print(f"  ✓ 删除菜单")
        total_deleted['menus'] += 1
    
    # 检查是否还有 moderation_admin 角色的其他菜单权限
    print("\n" + "=" * 80)
    print("检查 moderation_admin 角色")
    print("=" * 80)
    
    from mainotebook.system.models import Role
    moderation_admin_role = Role.objects.filter(key='moderation_admin').first()
    
    if moderation_admin_role:
        remaining_permissions = RoleMenuPermission.objects.filter(
            role=moderation_admin_role
        ).count()
        
        if remaining_permissions == 0:
            print(f"\n⚠️  moderation_admin 角色没有任何菜单权限了")
            print(f"   建议：考虑删除该角色或为其分配新的权限")
        else:
            print(f"\n✓ moderation_admin 角色还有 {remaining_permissions} 个菜单权限")
    
    # 打印总结
    print("\n" + "=" * 80)
    print("删除完成")
    print("=" * 80)
    print(f"删除的菜单数：{total_deleted['menus']}")
    print(f"删除的菜单按钮数：{total_deleted['buttons']}")
    print(f"删除的角色菜单权限数：{total_deleted['role_menu_permissions']}")
    print(f"删除的角色按钮权限数：{total_deleted['role_button_permissions']}")
    print("=" * 80)
    
    return True


if __name__ == '__main__':
    try:
        success = remove_obsolete_menus()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ 错误：{str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python
"""检查菜单配置"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()

from mainotebook.system.models import Menu, RoleMenuPermission, MenuButton

# 检查菜单
print("=" * 60)
print("检查新增菜单")
print("=" * 60)

menus = Menu.objects.filter(name__in=['知识库广场', '人设卡广场'])
for menu in menus:
    print(f"\n菜单: {menu.name}")
    print(f"  路由: {menu.web_path}")
    print(f"  组件: {menu.component}")
    print(f"  组件名: {menu.component_name}")
    print(f"  排序: {menu.sort}")
    print(f"  状态: {'启用' if menu.status else '禁用'}")
    print(f"  可见: {'是' if menu.visible else '否'}")
    
    # 检查按钮权限
    buttons = MenuButton.objects.filter(menu=menu)
    if buttons.exists():
        print(f"  按钮权限:")
        for btn in buttons:
            print(f"    - {btn.name} ({btn.value})")
    
    # 检查角色权限
    perms = RoleMenuPermission.objects.filter(menu=menu)
    if perms.exists():
        print(f"  角色权限:")
        for perm in perms:
            print(f"    - {perm.role.name} ({perm.role.key})")

print("\n" + "=" * 60)
print("检查完成")
print("=" * 60)

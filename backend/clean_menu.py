#!/usr/bin/env python
"""清除菜单数据"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()

from mainotebook.system.models import Menu, MenuButton, RoleMenuPermission, RoleMenuButtonPermission

print("开始清除菜单数据...")

# 删除角色按钮权限
count = RoleMenuButtonPermission.objects.all().delete()[0]
print(f"删除角色按钮权限: {count} 条")

# 删除角色菜单权限
count = RoleMenuPermission.objects.all().delete()[0]
print(f"删除角色菜单权限: {count} 条")

# 删除菜单按钮
count = MenuButton.objects.all().delete()[0]
print(f"删除菜单按钮: {count} 条")

# 删除菜单
count = Menu.objects.all().delete()[0]
print(f"删除菜单: {count} 条")

print("清除完成！")

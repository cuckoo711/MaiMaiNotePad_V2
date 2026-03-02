#!/usr/bin/env python
"""检查广场菜单"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()

from mainotebook.system.models import Menu

# 检查广场菜单
square_menu = Menu.objects.filter(name='广场').first()
if square_menu:
    print(f"✅ 找到广场菜单")
    print(f"  路由: {square_menu.web_path}")
    print(f"  排序: {square_menu.sort}")
    print(f"  是否目录: {square_menu.is_catalog}")
    print(f"  状态: {'启用' if square_menu.status else '禁用'}")
    
    # 检查子菜单
    children = Menu.objects.filter(parent=square_menu)
    print(f"\n  子菜单数量: {children.count()}")
    for child in children:
        print(f"    - {child.name} ({child.web_path})")
else:
    print("❌ 未找到广场菜单")

#!/usr/bin/env python
"""
检查重复菜单

检查数据库中是否存在重复的菜单记录
"""
import os
import sys
import django

# 设置Django环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()

from mainotebook.system.models import Menu
from django.db.models import Count

def check_duplicates():
    """检查重复菜单"""
    
    print("=" * 80)
    print("检查重复菜单")
    print("=" * 80)
    
    # 检查违规处理相关的菜单
    print("\n【1】检查违规处理相关菜单...")
    moderation_menus = Menu.objects.filter(web_path__startswith="/moderation")
    
    for menu in moderation_menus:
        print(f"\n  菜单: {menu.name}")
        print(f"    路径: {menu.web_path}")
        print(f"    组件: {menu.component}")
        print(f"    组件名: {menu.component_name}")
        print(f"    ID: {menu.id}")
        print(f"    父菜单: {menu.parent.name if menu.parent else 'None'}")
    
    # 检查是否有重复的name + web_path + component + component_name组合
    print("\n【2】检查unique_fields组合重复...")
    duplicates = Menu.objects.values('name', 'web_path', 'component', 'component_name').annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    if duplicates:
        print("  发现重复记录:")
        for dup in duplicates:
            print(f"    - {dup['name']} ({dup['web_path']}, {dup['component']}, {dup['component_name']}): {dup['count']}条")
            
            # 显示具体的重复记录
            menus = Menu.objects.filter(
                name=dup['name'],
                web_path=dup['web_path'],
                component=dup['component'],
                component_name=dup['component_name']
            )
            for menu in menus:
                print(f"      ID: {menu.id}, 创建时间: {menu.create_datetime}")
    else:
        print("  ✓ 没有发现重复记录")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    try:
        check_duplicates()
    except Exception as e:
        print(f"检查失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

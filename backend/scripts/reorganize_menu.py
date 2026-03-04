#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
菜单重组脚本

将"内容管理"菜单拆分为更合理的结构：
1. 内容管理：知识库管理、人设卡管理
2. 社区管理：评论管理
3. 审核管理：内容审核、AI审核日志、AI模型管理
"""

import json
import os
from pathlib import Path


def reorganize_menu():
    """重新组织菜单结构"""
    
    # 获取菜单文件路径
    script_dir = Path(__file__).parent
    menu_file = script_dir.parent / 'mainotebook' / 'system' / 'fixtures' / 'init_menu.json'
    
    print(f"正在读取菜单文件: {menu_file}")
    
    # 读取原始菜单
    with open(menu_file, 'r', encoding='utf-8') as f:
        menus = json.load(f)
    
    # 找到"内容管理"菜单的索引
    content_mgmt_index = None
    for i, menu in enumerate(menus):
        if menu.get('name') == '内容管理':
            content_mgmt_index = i
            break
    
    if content_mgmt_index is None:
        print("错误：未找到'内容管理'菜单")
        return
    
    print(f"找到'内容管理'菜单，索引: {content_mgmt_index}")
    
    # 获取原始的内容管理菜单
    original_content_menu = menus[content_mgmt_index]
    children = original_content_menu.get('children', [])
    
    # 分类子菜单
    knowledge_menu = None
    persona_menu = None
    comment_menu = None
    review_menu = None
    ai_log_menu = None
    ai_model_menu = None
    
    for child in children:
        name = child.get('name')
        if name == '知识库管理':
            knowledge_menu = child
        elif name == '人设卡管理':
            persona_menu = child
        elif name == '评论管理':
            comment_menu = child
        elif name == '内容审核':
            review_menu = child
        elif name == 'AI审核日志':
            ai_log_menu = child
        elif name == 'AI模型管理':
            ai_model_menu = child
    
    # 创建新的菜单结构
    
    # 1. 内容管理（只保留知识库和人设卡）
    new_content_menu = {
        "name": "内容管理",
        "icon": "ele-Folder",
        "sort": 10,
        "is_link": False,
        "is_catalog": True,
        "web_path": "/content",
        "component": "",
        "component_name": "",
        "status": True,
        "cache": False,
        "visible": True,
        "children": [knowledge_menu, persona_menu] if knowledge_menu and persona_menu else [],
        "menu_button": [],
        "menu_field": []
    }
    
    # 2. 社区管理（评论管理）
    community_menu = {
        "name": "社区管理",
        "icon": "ele-ChatDotRound",
        "sort": 11,
        "is_link": False,
        "is_catalog": True,
        "web_path": "/community",
        "component": "",
        "component_name": "",
        "status": True,
        "cache": False,
        "visible": True,
        "children": [comment_menu] if comment_menu else [],
        "menu_button": [],
        "menu_field": []
    }
    
    # 3. 审核管理（内容审核、AI审核日志、AI模型管理）
    review_mgmt_menu = {
        "name": "审核管理",
        "icon": "ele-Checked",
        "sort": 12,
        "is_link": False,
        "is_catalog": True,
        "web_path": "/review-management",
        "component": "",
        "component_name": "",
        "status": True,
        "cache": False,
        "visible": True,
        "children": [],
        "menu_button": [],
        "menu_field": []
    }
    
    # 添加审核管理的子菜单
    if review_menu:
        review_mgmt_menu['children'].append(review_menu)
    if ai_log_menu:
        ai_log_menu['sort'] = 2  # 调整排序
        review_mgmt_menu['children'].append(ai_log_menu)
    if ai_model_menu:
        ai_model_menu['sort'] = 3  # 调整排序
        review_mgmt_menu['children'].append(ai_model_menu)
    
    # 替换原有菜单
    menus[content_mgmt_index] = new_content_menu
    
    # 在内容管理后面插入社区管理和审核管理
    menus.insert(content_mgmt_index + 1, community_menu)
    menus.insert(content_mgmt_index + 2, review_mgmt_menu)
    
    # 保存修改后的菜单
    backup_file = menu_file.parent / 'init_menu.json.backup'
    if not backup_file.exists():
        print(f"创建备份文件: {backup_file}")
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(json.load(open(menu_file, 'r', encoding='utf-8')), f, ensure_ascii=False, indent=4)
    
    print(f"保存新菜单到: {menu_file}")
    with open(menu_file, 'w', encoding='utf-8') as f:
        json.dump(menus, f, ensure_ascii=False, indent=4)
    
    print("\n菜单重组完成！")
    print("\n新的菜单结构：")
    print("📁 内容管理")
    print("  ├─ 📖 知识库管理")
    print("  └─ 👤 人设卡管理")
    print("\n💬 社区管理")
    print("  └─ 💬 评论管理")
    print("\n🔍 审核管理")
    print("  ├─ ✅ 内容审核")
    print("  ├─ 📄 AI审核日志")
    print("  └─ 🤖 AI模型管理")
    print("\n请运行以下命令重新初始化菜单：")
    print("  python manage.py init")


if __name__ == '__main__':
    reorganize_menu()

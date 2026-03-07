#!/usr/bin/env python
"""
诊断菜单按钮状态

检查数据库中违规处理相关的菜单和菜单按钮状态
"""
import os
import sys
import django

# 设置Django环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()

from mainotebook.system.models import Menu, MenuButton, RoleMenuButtonPermission

def diagnose():
    """诊断菜单按钮状态"""
    
    print("=" * 80)
    print("诊断违规处理菜单和按钮状态")
    print("=" * 80)
    
    # 1. 检查违规处理父菜单
    print("\n【1】检查违规处理父菜单...")
    parent_menu = Menu.objects.filter(name="违规处理", web_path="/moderation").first()
    if parent_menu:
        print(f"  ✓ 找到父菜单: {parent_menu.name} (ID: {parent_menu.id})")
    else:
        print("  ✗ 未找到父菜单")
        return
    
    # 2. 检查子菜单
    print("\n【2】检查子菜单...")
    child_menus = Menu.objects.filter(parent=parent_menu)
    for menu in child_menus:
        print(f"  - {menu.name} ({menu.web_path}) [ID: {menu.id}]")
    
    # 3. 检查每个子菜单的按钮
    print("\n【3】检查菜单按钮...")
    expected_buttons = {
        "处罚操作": ["punish:SearchUser", "punish:Mute", "punish:Ban", "punish:BatchMute", "punish:BatchBan", "punish:Detail"],
        "禁言列表": ["mute:Search", "mute:Unmute", "mute:ModifyDuration", "mute:BatchUnmute", "mute:Detail", "mute:Export"],
        "封禁列表": ["ban:Search", "ban:Unban", "ban:ModifyDuration", "ban:BatchUnban", "ban:Detail", "ban:Export"],
        "AI自动禁言": ["autoMute:Search", "autoMute:Unmute", "autoMute:ModifyDuration", "autoMute:Detail", "autoMute:Export"],
    }
    
    for menu in child_menus:
        print(f"\n  菜单: {menu.name}")
        buttons = MenuButton.objects.filter(menu=menu)
        print(f"    实际按钮数: {buttons.count()}")
        
        if menu.name in expected_buttons:
            expected = expected_buttons[menu.name]
            print(f"    期望按钮数: {len(expected)}")
            
            actual_values = set(buttons.values_list('value', flat=True))
            expected_values = set(expected)
            
            missing = expected_values - actual_values
            extra = actual_values - expected_values
            
            if missing:
                print(f"    ✗ 缺失按钮: {', '.join(missing)}")
            if extra:
                print(f"    ! 额外按钮: {', '.join(extra)}")
            if not missing and not extra:
                print(f"    ✓ 按钮完整")
            
            # 显示实际按钮
            for btn in buttons:
                print(f"      - {btn.name} ({btn.value})")
    
    # 4. 检查所有违规处理相关的MenuButton
    print("\n【4】检查所有违规处理相关的MenuButton...")
    all_expected_values = [
        "punish:SearchUser", "punish:Mute", "punish:Ban", "punish:BatchMute", "punish:BatchBan", "punish:Detail",
        "mute:Search", "mute:Unmute", "mute:ModifyDuration", "mute:BatchUnmute", "mute:Detail", "mute:Export",
        "ban:Search", "ban:Unban", "ban:ModifyDuration", "ban:BatchUnban", "ban:Detail", "ban:Export",
        "autoMute:Search", "autoMute:Unmute", "autoMute:ModifyDuration", "autoMute:Detail", "autoMute:Export",
    ]
    
    for value in all_expected_values:
        btn = MenuButton.objects.filter(value=value).first()
        if btn:
            print(f"  ✓ {value} (菜单: {btn.menu.name})")
        else:
            print(f"  ✗ {value} - 不存在")
    
    # 5. 检查权限关联
    print("\n【5】检查权限关联...")
    for value in all_expected_values:
        perms = RoleMenuButtonPermission.objects.filter(menu_button__value=value)
        if perms.exists():
            roles = ', '.join(perms.values_list('role__key', flat=True))
            print(f"  {value}: {roles}")
        else:
            print(f"  {value}: 无权限关联")
    
    print("\n" + "=" * 80)
    print("诊断完成")
    print("=" * 80)

if __name__ == '__main__':
    try:
        diagnose()
    except Exception as e:
        print(f"诊断失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

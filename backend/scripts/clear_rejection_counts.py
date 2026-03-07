#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""清空AI评论审核拒绝次数脚本

本脚本用于清空评论拒绝记录和AI自动禁言记录，重置用户的AI审核拒绝次数统计。

功能：
- 清空 CommentRejectionLog 表中的所有记录
- 可选清空 AI 自动禁言记录（UserMuteRecord 和 UserModerationLog）
- 支持按用户ID清空特定用户的记录
- 支持按时间范围清空记录
- 提供安全确认机制

使用方法：
    # 清空所有拒绝记录
    python scripts/clear_rejection_counts.py --all
    
    # 清空所有拒绝记录和AI自动禁言记录
    python scripts/clear_rejection_counts.py --all --include-mute
    
    # 清空特定用户的记录
    python scripts/clear_rejection_counts.py --user-id 123
    
    # 清空指定天数之前的记录
    python scripts/clear_rejection_counts.py --days 30
    
    # 跳过确认（危险操作）
    python scripts/clear_rejection_counts.py --all --force

注意事项：
- 此操作不可逆，请谨慎使用
- 清空记录后，用户的拒绝次数统计将重置为0
- 使用 --include-mute 会同时清空AI自动禁言记录
- 建议在执行前先备份数据库
"""

import os
import sys
import django
import argparse
from datetime import datetime, timedelta

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()

from mainotebook.content.models import CommentRejectionLog, UserMuteRecord, UserModerationLog
from mainotebook.system.models import Users


def get_ai_reviewer_id():
    """获取AI审核员用户ID
    
    Returns:
        str: AI审核员用户ID，如果不存在则返回None
    """
    ai_reviewer = Users.objects.filter(username='ai_reviewer').first()
    return str(ai_reviewer.id) if ai_reviewer else None


def confirm_action(message: str) -> bool:
    """确认操作
    
    Args:
        message: 确认消息
        
    Returns:
        bool: 用户是否确认
    """
    response = input(f"{message} (yes/no): ").strip().lower()
    return response in ['yes', 'y']


def clear_all_records(force: bool = False, include_mute: bool = False) -> dict:
    """清空所有评论拒绝记录
    
    Args:
        force: 是否跳过确认
        include_mute: 是否同时清空AI自动禁言记录
        
    Returns:
        dict: 删除的记录统计
    """
    rejection_count = CommentRejectionLog.objects.count()
    mute_count = 0
    log_count = 0
    
    if include_mute:
        ai_reviewer_id = get_ai_reviewer_id()
        if ai_reviewer_id:
            mute_count = UserMuteRecord.objects.filter(mute_type='auto').count()
            log_count = UserModerationLog.objects.filter(
                operator_id=ai_reviewer_id,
                operation_type='mute'
            ).count()
    
    if rejection_count == 0 and (not include_mute or (mute_count == 0 and log_count == 0)):
        print("✓ 没有需要清空的记录")
        return {'rejection': 0, 'mute': 0, 'log': 0}
    
    if not force:
        print(f"⚠️  警告：即将删除以下记录：")
        print(f"   - 评论拒绝记录：{rejection_count} 条")
        if include_mute:
            print(f"   - AI自动禁言记录：{mute_count} 条")
            print(f"   - AI禁言操作日志：{log_count} 条")
        if not confirm_action("确定要继续吗？"):
            print("✗ 操作已取消")
            return {'rejection': 0, 'mute': 0, 'log': 0}
    
    # 删除记录
    CommentRejectionLog.objects.all().delete()
    
    if include_mute:
        ai_reviewer_id = get_ai_reviewer_id()
        if ai_reviewer_id:
            UserMuteRecord.objects.filter(mute_type='auto').delete()
            UserModerationLog.objects.filter(
                operator_id=ai_reviewer_id,
                operation_type='mute'
            ).delete()
    
    print(f"✓ 成功清空记录：")
    print(f"   - 评论拒绝记录：{rejection_count} 条")
    if include_mute:
        print(f"   - AI自动禁言记录：{mute_count} 条")
        print(f"   - AI禁言操作日志：{log_count} 条")
    
    return {'rejection': rejection_count, 'mute': mute_count, 'log': log_count}


def clear_user_records(user_id: int, force: bool = False, include_mute: bool = False) -> dict:
    """清空特定用户的评论拒绝记录
    
    Args:
        user_id: 用户ID
        force: 是否跳过确认
        include_mute: 是否同时清空AI自动禁言记录
        
    Returns:
        dict: 删除的记录统计
    """
    # 检查用户是否存在
    try:
        user = Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        print(f"✗ 错误：用户 ID {user_id} 不存在")
        return {'rejection': 0, 'mute': 0, 'log': 0}
    
    rejection_count = CommentRejectionLog.objects.filter(user_id=user_id).count()
    mute_count = 0
    log_count = 0
    
    if include_mute:
        ai_reviewer_id = get_ai_reviewer_id()
        if ai_reviewer_id:
            mute_count = UserMuteRecord.objects.filter(user_id=user_id, mute_type='auto').count()
            log_count = UserModerationLog.objects.filter(
                target_user_id=user_id,
                operator_id=ai_reviewer_id,
                operation_type='mute'
            ).count()
    
    if rejection_count == 0 and (not include_mute or (mute_count == 0 and log_count == 0)):
        print(f"✓ 用户 {user.username} (ID: {user_id}) 没有相关记录")
        return {'rejection': 0, 'mute': 0, 'log': 0}
    
    if not force:
        print(f"⚠️  警告：即将删除用户 {user.username} (ID: {user_id}) 的以下记录：")
        print(f"   - 评论拒绝记录：{rejection_count} 条")
        if include_mute:
            print(f"   - AI自动禁言记录：{mute_count} 条")
            print(f"   - AI禁言操作日志：{log_count} 条")
        if not confirm_action("确定要继续吗？"):
            print("✗ 操作已取消")
            return {'rejection': 0, 'mute': 0, 'log': 0}
    
    # 删除记录
    CommentRejectionLog.objects.filter(user_id=user_id).delete()
    
    if include_mute:
        ai_reviewer_id = get_ai_reviewer_id()
        if ai_reviewer_id:
            UserMuteRecord.objects.filter(user_id=user_id, mute_type='auto').delete()
            UserModerationLog.objects.filter(
                target_user_id=user_id,
                operator_id=ai_reviewer_id,
                operation_type='mute'
            ).delete()
    
    print(f"✓ 成功清空用户 {user.username} 的记录：")
    print(f"   - 评论拒绝记录：{rejection_count} 条")
    if include_mute:
        print(f"   - AI自动禁言记录：{mute_count} 条")
        print(f"   - AI禁言操作日志：{log_count} 条")
    
    return {'rejection': rejection_count, 'mute': mute_count, 'log': log_count}


def clear_old_records(days: int, force: bool = False, include_mute: bool = False) -> dict:
    """清空指定天数之前的评论拒绝记录
    
    Args:
        days: 天数
        force: 是否跳过确认
        include_mute: 是否同时清空AI自动禁言记录
        
    Returns:
        dict: 删除的记录统计
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    rejection_count = CommentRejectionLog.objects.filter(create_datetime__lt=cutoff_date).count()
    mute_count = 0
    log_count = 0
    
    if include_mute:
        ai_reviewer_id = get_ai_reviewer_id()
        if ai_reviewer_id:
            mute_count = UserMuteRecord.objects.filter(
                mute_type='auto',
                create_datetime__lt=cutoff_date
            ).count()
            log_count = UserModerationLog.objects.filter(
                operator_id=ai_reviewer_id,
                operation_type='mute',
                create_datetime__lt=cutoff_date
            ).count()
    
    if rejection_count == 0 and (not include_mute or (mute_count == 0 and log_count == 0)):
        print(f"✓ 没有 {days} 天前的记录需要清空")
        return {'rejection': 0, 'mute': 0, 'log': 0}
    
    if not force:
        print(f"⚠️  警告：即将删除 {days} 天前（{cutoff_date.strftime('%Y-%m-%d %H:%M:%S')} 之前）的以下记录：")
        print(f"   - 评论拒绝记录：{rejection_count} 条")
        if include_mute:
            print(f"   - AI自动禁言记录：{mute_count} 条")
            print(f"   - AI禁言操作日志：{log_count} 条")
        if not confirm_action("确定要继续吗？"):
            print("✗ 操作已取消")
            return {'rejection': 0, 'mute': 0, 'log': 0}
    
    # 删除记录
    CommentRejectionLog.objects.filter(create_datetime__lt=cutoff_date).delete()
    
    if include_mute:
        ai_reviewer_id = get_ai_reviewer_id()
        if ai_reviewer_id:
            UserMuteRecord.objects.filter(
                mute_type='auto',
                create_datetime__lt=cutoff_date
            ).delete()
            UserModerationLog.objects.filter(
                operator_id=ai_reviewer_id,
                operation_type='mute',
                create_datetime__lt=cutoff_date
            ).delete()
    
    print(f"✓ 成功清空旧记录：")
    print(f"   - 评论拒绝记录：{rejection_count} 条")
    if include_mute:
        print(f"   - AI自动禁言记录：{mute_count} 条")
        print(f"   - AI禁言操作日志：{log_count} 条")
    
    return {'rejection': rejection_count, 'mute': mute_count, 'log': log_count}


def show_statistics():
    """显示当前统计信息"""
    rejection_count = CommentRejectionLog.objects.count()
    user_count = CommentRejectionLog.objects.values('user_id').distinct().count()
    auto_mute_count = UserMuteRecord.objects.filter(mute_type='auto').count()
    
    ai_reviewer_id = get_ai_reviewer_id()
    auto_mute_log_count = 0
    if ai_reviewer_id:
        auto_mute_log_count = UserModerationLog.objects.filter(
            operator_id=ai_reviewer_id,
            operation_type='mute'
        ).count()
    
    print("\n" + "=" * 60)
    print("当前AI审核相关记录统计")
    print("=" * 60)
    print(f"评论拒绝记录数：{rejection_count}")
    print(f"涉及用户数：{user_count}")
    print(f"AI自动禁言记录数：{auto_mute_count}")
    print(f"AI禁言操作日志数：{auto_mute_log_count}")
    
    if rejection_count > 0:
        # 显示拒绝次数最多的前5个用户
        from django.db.models import Count
        top_users = (
            CommentRejectionLog.objects
            .values('user_id', 'user__username')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )
        
        print("\n拒绝次数最多的用户（前5名）：")
        for i, item in enumerate(top_users, 1):
            username = item['user__username'] or f"用户ID: {item['user_id']}"
            print(f"  {i}. {username}: {item['count']} 次")
    
    if auto_mute_count > 0:
        # 显示AI自动禁言的用户
        auto_muted_users = (
            UserMuteRecord.objects
            .filter(mute_type='auto', is_active=True)
            .select_related('user')
            .values('user_id', 'user__username', 'muted_until')[:5]
        )
        
        if auto_muted_users:
            print("\n当前被AI自动禁言的用户（前5名）：")
            for i, item in enumerate(auto_muted_users, 1):
                username = item['user__username'] or f"用户ID: {item['user_id']}"
                muted_until = item['muted_until'].strftime('%Y-%m-%d %H:%M:%S') if item['muted_until'] else '永久'
                print(f"  {i}. {username}: 禁言至 {muted_until}")
    
    print("=" * 60 + "\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='清空AI评论审核拒绝次数',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 查看当前统计
  python scripts/clear_rejection_counts.py --stats
  
  # 清空所有拒绝记录
  python scripts/clear_rejection_counts.py --all
  
  # 清空所有拒绝记录和AI自动禁言记录
  python scripts/clear_rejection_counts.py --all --include-mute
  
  # 清空特定用户的记录
  python scripts/clear_rejection_counts.py --user-id 123 --include-mute
  
  # 清空30天前的记录
  python scripts/clear_rejection_counts.py --days 30
  
  # 跳过确认（危险）
  python scripts/clear_rejection_counts.py --all --force
        """
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='清空所有评论拒绝记录'
    )
    
    parser.add_argument(
        '--user-id',
        type=int,
        help='清空特定用户的记录（指定用户ID）'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        help='清空指定天数之前的记录'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='跳过确认提示（危险操作）'
    )
    
    parser.add_argument(
        '--include-mute',
        action='store_true',
        help='同时清空AI自动禁言记录和操作日志'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='仅显示统计信息，不执行清空操作'
    )
    
    args = parser.parse_args()
    
    # 如果没有指定任何操作，显示帮助信息
    if not any([args.all, args.user_id, args.days, args.stats]):
        parser.print_help()
        return
    
    # 显示统计信息
    if args.stats:
        show_statistics()
        return
    
    print("\n" + "=" * 60)
    print("清空AI评论审核拒绝次数")
    print("=" * 60 + "\n")
    
    # 执行清空操作
    result = {'rejection': 0, 'mute': 0, 'log': 0}
    
    if args.all:
        result = clear_all_records(args.force, args.include_mute)
    elif args.user_id:
        result = clear_user_records(args.user_id, args.force, args.include_mute)
    elif args.days:
        result = clear_old_records(args.days, args.force, args.include_mute)
    
    total_deleted = result['rejection'] + result['mute'] + result['log']
    
    if total_deleted > 0:
        print(f"\n✓ 操作完成，共删除 {total_deleted} 条记录")
        print("提示：用户的拒绝次数统计已重置")
        if args.include_mute:
            print("提示：AI自动禁言记录已清空")
        print()


if __name__ == '__main__':
    main()

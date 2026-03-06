"""数据清理命令：清理字典模型中的翻译数据

使用方法：
    python manage.py cleanup_translation_dict                    # 清理（需要确认）
    python manage.py cleanup_translation_dict --force            # 强制清理（跳过确认）
    python manage.py cleanup_translation_dict --backup           # 清理前备份
    python manage.py cleanup_translation_dict --backup --force   # 备份并强制清理
"""

import json
import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from mainotebook.system.models import Dictionary

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """清理字典模型中的翻译数据
    
    删除 Dictionary 模型中 toml_visualizer_blocks 和 toml_visualizer_tokens 
    类型的翻译数据。这些数据已经迁移到 Translation 模型中。
    
    支持功能：
        - 备份数据到 JSON 文件（--backup）
        - 跳过确认提示（--force）
        - 事务保护确保原子性
        - 详细的日志输出
    """
    
    help = '清理字典模型中的翻译数据'
    
    def add_arguments(self, parser):
        """添加命令行参数"""
        parser.add_argument(
            '--backup',
            action='store_true',
            help='备份数据到 JSON 文件'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='跳过确认提示'
        )
    
    def handle(self, *args, **options):
        """执行清理命令
        
        Args:
            *args: 位置参数
            **options: 命令行选项
        """
        backup = options['backup']
        force = options['force']
        
        self.stdout.write(
            self.style.WARNING('=' * 60)
        )
        self.stdout.write(
            self.style.WARNING('字典翻译数据清理工具')
        )
        self.stdout.write(
            self.style.WARNING('=' * 60)
        )
        
        # 需要清理的翻译类型
        translation_types = [
            'toml_visualizer_blocks',
            'toml_visualizer_tokens'
        ]
        
        # 查询要删除的记录
        to_delete = []
        for trans_type in translation_types:
            self.stdout.write(f"\n正在查询类型: {trans_type}")
            
            # 查询父记录
            parent = Dictionary.objects.filter(
                value=trans_type,
                parent__isnull=True
            ).first()
            
            if parent:
                to_delete.append(parent)
                self.stdout.write(f"  找到父记录: {parent.label} ({parent.value})")
                
                # 查询子记录
                children = Dictionary.objects.filter(parent=parent)
                child_count = children.count()
                to_delete.extend(children)
                self.stdout.write(f"  找到 {child_count} 条子记录")
            else:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ 未找到类型 {trans_type} 的父记录")
                )
        
        if not to_delete:
            self.stdout.write('\n' + self.style.WARNING("没有找到需要清理的数据"))
            return
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(f"总计找到 {len(to_delete)} 条记录需要删除")
        self.stdout.write('=' * 60)
        
        # 备份数据
        backup_file = None
        if backup:
            backup_file = f"translation_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            self.stdout.write(f"\n正在备份数据到: {backup_file}")
            
            try:
                backup_data = []
                for record in to_delete:
                    backup_data.append({
                        'id': str(record.id),
                        'label': record.label,
                        'value': record.value,
                        'parent_value': record.parent.value if record.parent else None,
                        'type': record.type,
                        'sort': record.sort,
                        'status': record.status,
                        'remark': record.remark,
                        'create_datetime': record.create_datetime.isoformat() if record.create_datetime else None,
                        'update_datetime': record.update_datetime.isoformat() if record.update_datetime else None,
                    })
                
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=2)
                
                self.stdout.write(
                    self.style.SUCCESS(f"✓ 数据已备份到: {backup_file}")
                )
            except Exception as e:
                error_msg = f"备份失败: {str(e)}"
                logger.error(error_msg)
                self.stdout.write(self.style.ERROR(f"✗ {error_msg}"))
                self.stdout.write(self.style.ERROR("清理操作已取消"))
                return
        
        # 确认删除
        if not force:
            self.stdout.write('\n' + self.style.WARNING('警告：此操作将永久删除这些记录！'))
            if backup_file:
                self.stdout.write(f"备份文件: {backup_file}")
            
            confirm = input("\n确认删除这些记录吗？(yes/no): ")
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING("\n操作已取消"))
                return
        
        # 执行删除
        self.stdout.write('\n正在删除记录...')
        try:
            with transaction.atomic():
                deleted_count = 0
                
                # 先删除子记录，再删除父记录
                for record in to_delete:
                    if record.parent is not None:
                        # 这是子记录
                        self.stdout.write(
                            f"  删除子记录: {record.value} -> {record.label}"
                        )
                        record.delete()
                        deleted_count += 1
                
                # 删除父记录
                for record in to_delete:
                    if record.parent is None:
                        # 这是父记录
                        self.stdout.write(
                            f"  删除父记录: {record.value}"
                        )
                        record.delete()
                        deleted_count += 1
                
                self.stdout.write('\n' + '=' * 60)
                self.stdout.write(
                    self.style.SUCCESS(f"✓ 成功删除 {deleted_count} 条记录")
                )
                self.stdout.write('=' * 60)
                
                if backup_file:
                    self.stdout.write(
                        self.style.SUCCESS(f"备份文件: {backup_file}")
                    )
                
        except Exception as e:
            error_msg = f"清理失败: {str(e)}"
            logger.error(error_msg)
            self.stdout.write('\n' + self.style.ERROR('=' * 60))
            self.stdout.write(self.style.ERROR(f"✗ {error_msg}"))
            self.stdout.write(self.style.ERROR('=' * 60))
            self.stdout.write(
                self.style.ERROR('事务已回滚，数据未被删除')
            )
            
            if backup_file:
                self.stdout.write(f"备份文件已保留: {backup_file}")

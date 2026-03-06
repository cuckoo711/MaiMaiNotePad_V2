"""数据迁移命令：将字典模型中的翻译数据迁移到翻译模型

使用方法：
    python manage.py migrate_translation              # 正式迁移
    python manage.py migrate_translation --dry-run    # 模拟运行
"""

import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from mainotebook.system.models import Dictionary, Translation

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """将字典模型中的翻译数据迁移到翻译模型
    
    从 Dictionary 模型中查询 toml_visualizer_blocks 和 toml_visualizer_tokens 
    类型的翻译数据，转换字段映射后保存到 Translation 模型。
    
    字段映射：
        - Dictionary.label -> Translation.translated_text
        - Dictionary.value -> Translation.source_text
        - Dictionary.sort -> Translation.sort
        - Dictionary.status -> Translation.status
    """
    
    help = '将字典模型中的翻译数据迁移到翻译模型'
    
    def add_arguments(self, parser):
        """添加命令行参数"""
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='模拟运行，不实际保存数据'
        )
    
    def handle(self, *args, **options):
        """执行迁移命令
        
        Args:
            *args: 位置参数
            **options: 命令行选项
        """
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('=' * 60)
            )
            self.stdout.write(
                self.style.WARNING('模拟运行模式 - 不会实际保存数据')
            )
            self.stdout.write(
                self.style.WARNING('=' * 60)
            )
        
        # 需要迁移的翻译类型
        translation_types = [
            'toml_visualizer_blocks',
            'toml_visualizer_tokens'
        ]
        
        success_count = 0
        error_count = 0
        skip_count = 0
        
        for trans_type in translation_types:
            self.stdout.write(f"\n正在迁移类型: {trans_type}")
            self.stdout.write('-' * 60)
            
            # 查询父记录
            parent = Dictionary.objects.filter(
                value=trans_type,
                parent__isnull=True
            ).first()
            
            if not parent:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ 未找到类型 {trans_type} 的父记录")
                )
                continue
            
            # 查询子记录（实际的翻译数据）
            children = Dictionary.objects.filter(parent=parent)
            
            if not children.exists():
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ 类型 {trans_type} 下没有翻译数据")
                )
                continue
            
            self.stdout.write(f"  找到 {children.count()} 条翻译数据")
            
            # 迁移每条子记录
            for child in children:
                try:
                    # 检查是否已存在
                    existing = Translation.objects.filter(
                        translation_type=trans_type,
                        source_text=child.value
                    ).first()
                    
                    if existing:
                        skip_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⊙ 跳过已存在: {child.value} -> {child.label}"
                            )
                        )
                        continue
                    
                    if not dry_run:
                        # 使用事务确保数据一致性
                        with transaction.atomic():
                            Translation.objects.create(
                                translation_type=trans_type,
                                source_text=child.value,
                                translated_text=child.label,
                                source_language='en',
                                target_language='zh',
                                sort=child.sort if child.sort else 1,
                                status=child.status
                            )
                    
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ {child.value} -> {child.label}"
                        )
                    )
                    
                except Exception as e:
                    error_count += 1
                    error_msg = f"迁移失败: {child.value}, 错误: {str(e)}"
                    logger.error(error_msg)
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ {child.value}: {str(e)}")
                    )
        
        # 输出统计信息
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('迁移完成！'))
        self.stdout.write('=' * 60)
        self.stdout.write(f"成功: {success_count} 条")
        self.stdout.write(f"跳过: {skip_count} 条（已存在）")
        self.stdout.write(f"失败: {error_count} 条")
        self.stdout.write(f"总计: {success_count + skip_count + error_count} 条")
        
        if dry_run:
            self.stdout.write('\n' + self.style.WARNING(
                '这是模拟运行，未实际保存数据。'
            ))
            self.stdout.write(self.style.WARNING(
                '要正式迁移，请运行: python manage.py migrate_translation'
            ))
        
        if error_count > 0:
            self.stdout.write('\n' + self.style.ERROR(
                f'有 {error_count} 条记录迁移失败，请检查日志获取详细信息。'
            ))

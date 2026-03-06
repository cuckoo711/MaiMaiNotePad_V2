"""
清理测试翻译数据的管理命令

使用方法：
    python manage.py clean_test_translations
"""

from django.core.management.base import BaseCommand
from mainotebook.system.models import Translation


class Command(BaseCommand):
    """清理测试翻译数据"""
    
    help = '清理测试翻译数据'

    def handle(self, *args, **options):
        """执行清理操作"""
        self.stdout.write(self.style.WARNING('开始清理测试翻译数据...'))
        
        # 查询所有翻译记录
        all_translations = Translation.objects.all()
        total_count = all_translations.count()
        
        self.stdout.write(f'找到 {total_count} 条翻译记录')
        
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('没有需要清理的数据'))
            return
        
        # 显示所有记录
        self.stdout.write('\n当前翻译记录：')
        for trans in all_translations:
            self.stdout.write(
                f'  ID: {trans.id}, '
                f'类型: {trans.translation_type}, '
                f'原文: {trans.source_text}, '
                f'译文: {trans.translated_text}'
            )
        
        # 询问用户是否确认删除
        confirm = input('\n是否删除所有测试数据？(yes/no): ')
        
        if confirm.lower() in ['yes', 'y']:
            deleted_count, _ = all_translations.delete()
            self.stdout.write(
                self.style.SUCCESS(f'成功删除 {deleted_count} 条测试数据')
            )
        else:
            self.stdout.write(self.style.WARNING('取消删除操作'))

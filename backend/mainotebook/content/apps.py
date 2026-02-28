"""
Content 应用配置模块
"""

from django.apps import AppConfig


class ContentConfig(AppConfig):
    """Content 应用配置类"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mainotebook.content'
    verbose_name = '内容管理'
    
    def ready(self):
        """应用就绪时执行的初始化操作"""
        pass

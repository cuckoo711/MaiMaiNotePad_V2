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
        # 注册 AIModel 的 post_save/post_delete signal，自动重算优先级
        import mainotebook.content.views.ai_model  # noqa: F401

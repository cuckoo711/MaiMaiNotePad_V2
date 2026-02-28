from django.apps import AppConfig


class SystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mainotebook.system'

    def ready(self):
        # 注册信号
        import mainotebook.system.signals  # 确保路径正确

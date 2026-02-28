"""pytest 配置文件

配置 Django 测试环境。
"""

import django
from django.conf import settings


def pytest_configure():
    """配置 pytest-django 使用正确的 Django 设置模块"""
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
    django.setup()

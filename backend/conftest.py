"""pytest 配置文件

配置 Django 测试环境。
"""

import django
from django.conf import settings
import pytest


def pytest_configure():
    """配置 pytest-django 使用正确的 Django 设置模块"""
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
    django.setup()


@pytest.fixture(scope='session')
def django_db_setup():
    """配置测试数据库
    
    确保测试使用独立的测试数据库，而不是生产数据库。
    Django 会自动创建名为 test_<DATABASE_NAME> 的测试数据库。
    """
    from django.conf import settings
    
    # 确保使用测试数据库
    settings.DATABASES['default']['TEST'] = {
        'NAME': f"test_{settings.DATABASES['default']['NAME']}",
        'MIRROR': None,
    }

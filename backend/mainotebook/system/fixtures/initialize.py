# 初始化
import os
import sys

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "application.settings")
django.setup()

from mainotebook.utils.core_initialize import CoreInitialize
from mainotebook.system.fixtures.initSerializer import (
    UsersInitSerializer, DeptInitSerializer, RoleInitSerializer,
    MenuInitSerializer, ApiWhiteListInitSerializer, DictionaryInitSerializer,
    SystemConfigInitSerializer, RoleMenuInitSerializer, RoleMenuButtonInitSerializer
)


class Initialize(CoreInitialize):
    """麦麦笔记本系统初始化

    负责初始化部门、角色、用户、菜单、权限、字典、系统配置等基础数据。
    """

    def init_dept(self):
        """初始化部门信息"""
        self.init_base(DeptInitSerializer, unique_fields=['name', 'parent', 'key'])

    def init_role(self):
        """初始化角色信息"""
        self.init_base(RoleInitSerializer, unique_fields=['key'])

    def init_users(self):
        """初始化用户信息"""
        self.init_base(UsersInitSerializer, unique_fields=['username'])

    def init_menu(self):
        """初始化菜单信息"""
        self.init_base(MenuInitSerializer, unique_fields=['name', 'web_path', 'component', 'component_name'])

    def init_role_menu(self):
        """初始化角色菜单权限"""
        self.init_base(RoleMenuInitSerializer, unique_fields=['role__key', 'menu__web_path', 'menu__component_name'])

    def init_role_menu_button(self):
        """初始化角色菜单按钮权限"""
        self.init_base(RoleMenuButtonInitSerializer, unique_fields=['role__key', 'menu_button__value'])

    def init_api_white_list(self):
        """初始化 API 白名单"""
        self.init_base(ApiWhiteListInitSerializer, unique_fields=['url', 'method'])

    def init_dictionary(self):
        """初始化字典表"""
        self.init_base(DictionaryInitSerializer, unique_fields=['value', 'parent'])

    def init_system_config(self):
        """初始化系统配置表"""
        self.init_base(SystemConfigInitSerializer, unique_fields=['key', 'parent'])

    def init_test_users(self):
        """初始化测试用户（可选）

        为每个角色创建一个测试用户，用于开发和测试环境。
        测试用户文件：init_test_users.json
        """
        import json
        from django.apps import apps

        path_file = os.path.join(
            apps.get_app_config(self.app.split('.')[-1]).path,
            'fixtures',
            'init_test_users.json'
        )
        if not os.path.isfile(path_file):
            print("测试用户文件不存在，跳过")
            return

        model = UsersInitSerializer.Meta.model
        with open(path_file, encoding="utf-8") as f:
            for data in json.load(f):
                filter_data = {"username": data["username"]}
                instance = model.objects.filter(**filter_data).first()
                data["reset"] = self.reset
                serializer = UsersInitSerializer(instance, data=data, request=self.request)
                serializer.is_valid(raise_exception=True)
                serializer.save()
        print(f"[{self.app}][测试用户]初始化完成")

    def run(self):
        """执行基础数据初始化"""
        self.init_dept()
        self.init_role()
        self.init_users()
        self.init_menu()
        self.init_role_menu()
        self.init_role_menu_button()
        self.init_api_white_list()
        self.init_dictionary()
        self.init_system_config()

    def run_with_test_data(self):
        """执行基础数据初始化 + 测试用户

        在 run() 基础上额外创建测试用户，适用于开发和测试环境。
        """
        self.run()
        self.init_test_users()


if __name__ == "__main__":
    # 默认只初始化基础数据
    # 传入 --test 参数可同时创建测试用户
    include_test = "--test" in sys.argv
    initializer = Initialize(app='mainotebook.system')

    if include_test:
        print("🧪 包含测试用户初始化...")
        initializer.run_with_test_data()
    else:
        initializer.run()

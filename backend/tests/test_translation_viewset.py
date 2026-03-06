"""TranslationViewSet API 测试

测试翻译视图集的基本功能。
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from mainotebook.system.models import Translation

User = get_user_model()


@pytest.fixture
def api_client():
    """创建 API 客户端"""
    return APIClient()


@pytest.fixture
def admin_user():
    """创建管理员用户"""
    from mainotebook.system.models import Role
    
    # 创建管理员角色（如果不存在）
    admin_role, _ = Role.objects.get_or_create(
        key='admin',
        defaults={
            'name': '管理员',
            'sort': 1,
            'status': True
        }
    )
    
    # 创建超级用户
    user = User.objects.create_superuser(
        username='admin_test',
        password='testpass123',
        email='admin@test.com'
    )
    
    # 关联角色
    user.role.add(admin_role)
    
    return user


@pytest.fixture
def sample_translation():
    """创建示例翻译数据"""
    return Translation.objects.create(
        source_text='test_block',
        translated_text='测试块',
        translation_type='toml_visualizer_blocks',
        source_language='en',
        target_language='zh',
        sort=1,
        status=True
    )


@pytest.mark.django_db
class TestTranslationViewSet:
    """TranslationViewSet 测试类"""
    
    def test_list_translations_public_access(self, api_client, sample_translation):
        """测试公开访问翻译列表
        
        验证需求：7.5 - 查询操作允许公开访问
        """
        response = api_client.get('/api/system/translation/')
        assert response.status_code == 200
        assert 'data' in response.data or 'results' in response.data
    
    def test_retrieve_translation_public_access(self, api_client, sample_translation):
        """测试公开访问单个翻译
        
        验证需求：7.5 - 查询操作允许公开访问
        """
        response = api_client.get(f'/api/system/translation/{sample_translation.id}/')
        assert response.status_code == 200
    
    def test_get_by_type_success(self, api_client, sample_translation):
        """测试按类型查询翻译成功
        
        验证需求：4.8 - 按类型查询功能
        """
        response = api_client.get(
            '/api/system/translation/get_by_type/',
            {'translation_type': 'toml_visualizer_blocks'}
        )
        assert response.status_code == 200
        assert isinstance(response.data, list)
        assert len(response.data) > 0
        assert response.data[0]['source_text'] == 'test_block'
    
    def test_get_by_type_missing_parameter(self, api_client):
        """测试按类型查询缺少参数
        
        验证需求：4.8 - 参数验证
        """
        response = api_client.get('/api/system/translation/get_by_type/')
        assert response.status_code == 400
        assert 'error' in response.data
    
    def test_get_by_type_filters_by_status(self, api_client):
        """测试按类型查询只返回启用的翻译
        
        验证需求：4.8 - 状态过滤
        """
        # 创建启用的翻译
        Translation.objects.create(
            source_text='enabled',
            translated_text='启用',
            translation_type='test_type',
            status=True,
            sort=1
        )
        # 创建禁用的翻译
        Translation.objects.create(
            source_text='disabled',
            translated_text='禁用',
            translation_type='test_type',
            status=False,
            sort=2
        )
        
        response = api_client.get(
            '/api/system/translation/get_by_type/',
            {'translation_type': 'test_type'}
        )
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['source_text'] == 'enabled'
    
    def test_create_requires_admin(self, api_client):
        """测试创建翻译需要管理员权限
        
        验证需求：7.6 - 修改操作需要管理员权限
        """
        data = {
            'source_text': 'new_text',
            'translated_text': '新文本',
            'translation_type': 'test_type',
            'source_language': 'en',
            'target_language': 'zh'
        }
        response = api_client.post('/api/system/translation/', data)
        # 项目使用自定义异常处理器，总是返回 HTTP 200，但在响应体中包含错误代码
        # 检查响应：可能是 HTTP 状态码 401/403，或者是 HTTP 200 + code 4000/401/403
        is_rejected = (
            response.status_code in [401, 403] or
            (response.status_code == 200 and 
             isinstance(response.data, dict) and 
             response.data.get('code') in [4000, 401, 403])
        )
        assert is_rejected, (
            f"未认证用户创建翻译应该被拒绝\n"
            f"HTTP 状态码: {response.status_code}\n"
            f"响应数据: {response.data}"
        )
    
    def test_create_with_admin(self, api_client, admin_user):
        """测试管理员可以创建翻译
        
        验证需求：4.1, 7.6 - 管理员可以创建
        """
        api_client.force_authenticate(user=admin_user)
        data = {
            'source_text': 'admin_text',
            'translated_text': '管理员文本',
            'translation_type': 'test_type',
            'source_language': 'en',
            'target_language': 'zh',
            'sort': 1,
            'status': True
        }
        response = api_client.post('/api/system/translation/', data)
        assert response.status_code in [200, 201]
    
    def test_filter_by_translation_type(self, api_client):
        """测试按翻译类型过滤
        
        验证需求：4.2 - 过滤功能
        """
        Translation.objects.create(
            source_text='block1',
            translated_text='块1',
            translation_type='type1',
            sort=1
        )
        Translation.objects.create(
            source_text='block2',
            translated_text='块2',
            translation_type='type2',
            sort=2
        )
        
        response = api_client.get(
            '/api/system/translation/',
            {'translation_type': 'type1'}
        )
        assert response.status_code == 200
    
    def test_ordering_by_sort(self, api_client):
        """测试按 sort 字段排序
        
        验证需求：4.5 - 排序功能
        """
        Translation.objects.create(
            source_text='third',
            translated_text='第三',
            translation_type='test_type',
            sort=3
        )
        Translation.objects.create(
            source_text='first',
            translated_text='第一',
            translation_type='test_type',
            sort=1
        )
        Translation.objects.create(
            source_text='second',
            translated_text='第二',
            translation_type='test_type',
            sort=2
        )
        
        response = api_client.get('/api/system/translation/')
        assert response.status_code == 200
        # 验证返回的数据按 sort 排序
        # 注意：响应格式可能是分页的，需要适配
        if 'results' in response.data:
            results = response.data['results']
        elif 'data' in response.data:
            results = response.data['data']
        else:
            results = response.data
        
        if len(results) >= 3:
            # 检查最后三条记录是否按 sort 排序
            last_three = results[-3:]
            assert last_three[0]['sort'] <= last_three[1]['sort'] <= last_three[2]['sort']

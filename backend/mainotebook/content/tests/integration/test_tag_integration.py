# -*- coding: utf-8 -*-

"""
标签集成测试

测试端到端的标签处理流程，验证从 API 请求到数据库存储的完整链路。

注意：本项目使用自定义响应格式，成功时返回 HTTP 200 和 code=2000，
而不是标准的 REST 状态码（如 201）。
"""

import pytest
from rest_framework.test import APITestCase
from rest_framework import status
from mainotebook.content.models import PersonaCard, KnowledgeBase
from mainotebook.system.models import Users


class TestPersonaCardTagIntegration(APITestCase):
    """人设卡标签集成测试
    
    测试使用数组格式和字符串格式创建人设卡，验证 API 响应标签标准化。
    """
    
    def setUp(self):
        """设置测试用户和 HTTP 头"""
        self.user = Users.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com',
            name='测试用户'
        )
        self.client.force_authenticate(user=self.user)
        # 设置默认的 HTTP 头，避免中间件错误
        self.client.defaults['HTTP_USER_AGENT'] = 'TestClient/1.0'
    
    def test_create_persona_card_with_array_tags(self):
        """测试使用数组格式创建人设卡
        
        验证需求：10.5
        """
        data = {
            'name': '测试卡片',
            'description': '这是一个测试人设卡的描述内容',
            'tags': ['标签1', '标签2', '标签3']
        }
        
        response = self.client.post('/api/content/persona/', data, format='json')
        
        # 项目使用自定义响应格式，成功时返回 200 和 code=2000
        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 2000
        assert 'data' in response.data
        assert response.data['data']['tags'] == ['标签1', '标签2', '标签3']
        
        # 验证数据库中的数据
        card = PersonaCard.objects.get(name='测试卡片')
        assert card.tags == ['标签1', '标签2', '标签3']
        assert isinstance(card.tags, list)
    
    def test_create_persona_card_with_string_tags(self):
        """测试使用字符串格式创建人设卡（向后兼容）
        
        验证需求：10.5, 3.2
        """
        data = {
            'name': '测试卡片2',
            'description': '这是一个测试描述内容',
            'tags': '标签1,标签2,标签3'
        }
        
        response = self.client.post('/api/content/persona/', data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 2000
        # API 应该返回数组格式
        assert 'data' in response.data
        assert response.data['data']['tags'] == ['标签1', '标签2', '标签3']
        
        # 验证数据库中存储为数组
        card = PersonaCard.objects.get(name='测试卡片2')
        assert card.tags == ['标签1', '标签2', '标签3']
        assert isinstance(card.tags, list)
    
    def test_api_response_normalized_tags(self):
        """测试 API 响应标签标准化
        
        Feature: tags-array-migration, Property 8: API 响应标签标准化
        验证需求：8.3, 8.4
        """
        # 创建带有重复和空格的标签
        card = PersonaCard.objects.create(
            name='测试卡片3',
            description='这是一个测试人设卡的描述内容',
            uploader=self.user,
            tags=['  标签1  ', '标签2', '标签1', '', '标签3']
        )
        
        response = self.client.get(f'/api/content/persona/{card.id}/')
        
        # 验证响应标签已标准化
        assert response.status_code == status.HTTP_200_OK
        assert 'data' in response.data
        tags = response.data['data']['tags']
        assert isinstance(tags, list), "标签应该是数组格式"
        assert all(tag == tag.strip() for tag in tags), "所有标签应该去除空格"
        assert len(tags) == len(set(tags)), "不应该有重复标签"
        assert all(tag for tag in tags), "不应该有空字符串"
    
    def test_create_with_empty_tags(self):
        """测试创建人设卡时标签为空"""
        data = {
            'name': '测试卡片4',
            'description': '这是一个测试描述内容',
            'tags': []
        }
        
        response = self.client.post('/api/content/persona/', data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 2000
        assert 'data' in response.data
        assert response.data['data']['tags'] == []
    
    def test_create_with_null_tags(self):
        """测试创建人设卡时标签为 null"""
        data = {
            'name': '测试卡片5',
            'description': '这是一个测试描述内容',
            'tags': None
        }
        
        response = self.client.post('/api/content/persona/', data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 2000
        assert 'data' in response.data
        assert response.data['data']['tags'] == []
    
    def test_update_persona_card_tags(self):
        """测试更新人设卡标签"""
        # 创建人设卡
        card = PersonaCard.objects.create(
            name='测试卡片6',
            description='这是一个测试人设卡的描述内容',
            uploader=self.user,
            tags=['旧标签1', '旧标签2']
        )
        
        # 更新标签
        data = {
            'tags': ['新标签1', '新标签2', '新标签3']
        }
        
        response = self.client.patch(f'/api/content/persona/{card.id}/', data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 2000
        assert 'data' in response.data
        assert response.data['data']['tags'] == ['新标签1', '新标签2', '新标签3']
        
        # 验证数据库
        card.refresh_from_db()
        assert card.tags == ['新标签1', '新标签2', '新标签3']
    
    def test_tag_validation_max_length(self):
        """测试标签长度验证"""
        long_tag = '标' * 51  # 超过 50 字符
        data = {
            'name': '测试卡片7',
            'description': '这是一个测试描述内容',
            'tags': [long_tag]
        }
        
        response = self.client.post('/api/content/persona/', data, format='json')
        
        # 项目使用自定义响应格式，验证失败时返回 200 和 code=4000
        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 4000
        assert '超过最大长度' in str(response.data) or '50' in str(response.data)
    
    def test_tag_validation_max_count(self):
        """测试标签数量验证"""
        tags = [f'标签{i}' for i in range(21)]  # 超过 20 个
        data = {
            'name': '测试卡片8',
            'description': '这是一个测试描述内容',
            'tags': tags
        }
        
        response = self.client.post('/api/content/persona/', data, format='json')
        
        # 项目使用自定义响应格式，验证失败时返回 200 和 code=4000
        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 4000
        assert '超过最大限制' in str(response.data) or '20' in str(response.data)


class TestKnowledgeBaseTagIntegration(APITestCase):
    """知识库标签集成测试
    
    测试使用数组格式和字符串格式创建知识库，验证 API 响应标签标准化。
    """
    
    def setUp(self):
        """设置测试用户和 HTTP 头"""
        self.user = Users.objects.create_user(
            username='testuser_kb',
            password='testpass123',
            email='test_kb@example.com',
            name='测试用户KB'
        )
        self.client.force_authenticate(user=self.user)
        # 设置默认的 HTTP 头，避免中间件错误
        self.client.defaults['HTTP_USER_AGENT'] = 'TestClient/1.0'
    
    def test_create_knowledge_base_with_array_tags(self):
        """测试使用数组格式创建知识库
        
        验证需求：10.5
        """
        data = {
            'name': '测试知识库',
            'description': '这是一个测试描述内容',
            'tags': ['知识', '学习', '教程']
        }
        
        response = self.client.post('/api/content/knowledge/', data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 2000
        assert 'data' in response.data
        assert response.data['data']['tags'] == ['知识', '学习', '教程']
        
        # 验证数据库中的数据
        kb = KnowledgeBase.objects.get(name='测试知识库')
        assert kb.tags == ['知识', '学习', '教程']
        assert isinstance(kb.tags, list)
    
    def test_create_knowledge_base_with_string_tags(self):
        """测试使用字符串格式创建知识库（向后兼容）
        
        验证需求：10.5, 3.2
        """
        data = {
            'name': '测试知识库2',
            'description': '这是一个测试描述内容',
            'tags': '知识,学习,教程'
        }
        
        response = self.client.post('/api/content/knowledge/', data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 2000
        # API 应该返回数组格式
        assert 'data' in response.data
        assert response.data['data']['tags'] == ['知识', '学习', '教程']
        
        # 验证数据库中存储为数组
        kb = KnowledgeBase.objects.get(name='测试知识库2')
        assert kb.tags == ['知识', '学习', '教程']
        assert isinstance(kb.tags, list)
    
    def test_api_response_normalized_tags(self):
        """测试 API 响应标签标准化
        
        Feature: tags-array-migration, Property 8: API 响应标签标准化
        验证需求：8.3, 8.4
        """
        # 创建带有重复和空格的标签
        kb = KnowledgeBase.objects.create(
            name='测试知识库3',
            description='这是一个测试知识库的描述内容',
            uploader=self.user,
            tags=['  知识  ', '学习', '知识', '', '教程']
        )
        
        response = self.client.get(f'/api/content/knowledge/{kb.id}/')
        
        # 验证响应标签已标准化
        assert response.status_code == status.HTTP_200_OK
        assert 'data' in response.data
        tags = response.data['data']['tags']
        assert isinstance(tags, list), "标签应该是数组格式"
        assert all(tag == tag.strip() for tag in tags), "所有标签应该去除空格"
        assert len(tags) == len(set(tags)), "不应该有重复标签"
        assert all(tag for tag in tags), "不应该有空字符串"


class TestEndToEndTagWorkflow(APITestCase):
    """端到端标签处理流程测试
    
    测试完整的标签处理流程：创建 -> 查询 -> 更新
    """
    
    def setUp(self):
        """设置测试用户和 HTTP 头"""
        self.user = Users.objects.create_user(
            username='testuser_e2e',
            password='testpass123',
            email='test_e2e@example.com',
            name='测试用户E2E'
        )
        self.client.force_authenticate(user=self.user)
        # 设置默认的 HTTP 头，避免中间件错误
        self.client.defaults['HTTP_USER_AGENT'] = 'TestClient/1.0'
    
    def test_complete_tag_workflow(self):
        """测试完整的标签工作流
        
        工作流步骤：
        1. 使用字符串格式创建人设卡
        2. 验证 API 返回数组格式
        3. 查询人设卡，验证标签格式
        4. 使用数组格式更新标签
        5. 验证更新后的标签
        """
        # 步骤 1: 使用字符串格式创建
        create_data = {
            'name': '工作流测试卡片',
            'description': '测试完整工作流',
            'tags': '标签1,标签2,标签3'
        }
        
        create_response = self.client.post('/api/content/persona/', create_data, format='json')
        assert create_response.status_code == status.HTTP_200_OK
        assert create_response.data['code'] == 2000
        assert 'data' in create_response.data
        
        # 获取创建的卡片
        card = PersonaCard.objects.get(name='工作流测试卡片')
        card_id = card.id
        
        # 步骤 2: 验证 API 返回数组格式
        assert create_response.data['data']['tags'] == ['标签1', '标签2', '标签3']
        
        # 步骤 3: 查询人设卡
        get_response = self.client.get(f'/api/content/persona/{card_id}/')
        assert get_response.status_code == status.HTTP_200_OK
        assert 'data' in get_response.data
        assert get_response.data['data']['tags'] == ['标签1', '标签2', '标签3']
        
        # 步骤 4: 使用数组格式更新标签
        update_data = {
            'tags': ['新标签A', '新标签B']
        }
        
        update_response = self.client.patch(f'/api/content/persona/{card_id}/', update_data, format='json')
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.data['code'] == 2000
        
        # 步骤 5: 验证更新后的标签
        assert 'data' in update_response.data
        assert update_response.data['data']['tags'] == ['新标签A', '新标签B']
        
        # 再次查询验证
        final_response = self.client.get(f'/api/content/persona/{card_id}/')
        assert 'data' in final_response.data
        assert final_response.data['data']['tags'] == ['新标签A', '新标签B']
        
        # 验证数据库
        card.refresh_from_db()
        assert card.tags == ['新标签A', '新标签B']
    
    def test_tag_normalization_workflow(self):
        """测试标签标准化工作流
        
        测试带有空格、重复、空字符串的标签在整个流程中的处理
        """
        # 创建带有需要标准化的标签
        data = {
            'name': '标准化测试卡片',
            'description': '测试标签标准化',
            'tags': ['  标签1  ', '标签2', '标签1', '', '  标签3  ', '标签2']
        }
        
        response = self.client.post('/api/content/persona/', data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 2000
        assert 'data' in response.data
        
        # 验证标签已被标准化：去空格、去重、去空字符串
        tags = response.data['data']['tags']
        assert '标签1' in tags
        assert '标签2' in tags
        assert '标签3' in tags
        assert len(tags) == 3  # 去重后只有 3 个
        assert all(tag == tag.strip() for tag in tags)  # 所有标签都去除了空格
        assert all(tag for tag in tags)  # 没有空字符串
    
    def test_mixed_format_workflow(self):
        """测试混合格式工作流
        
        创建时使用字符串格式，更新时使用数组格式
        """
        # 创建：字符串格式
        create_data = {
            'name': '混合格式测试',
            'description': '这是一个测试描述内容',
            'tags': 'tag1,tag2,tag3'
        }
        
        create_response = self.client.post('/api/content/persona/', create_data, format='json')
        assert create_response.status_code == status.HTTP_200_OK
        assert create_response.data['code'] == 2000
        assert 'data' in create_response.data
        assert create_response.data['data']['tags'] == ['tag1', 'tag2', 'tag3']
        
        # 获取卡片 ID
        card = PersonaCard.objects.get(name='混合格式测试')
        card_id = card.id
        
        # 更新：数组格式
        update_data = {
            'tags': ['新tag1', '新tag2']
        }
        
        update_response = self.client.patch(f'/api/content/persona/{card_id}/', update_data, format='json')
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.data['code'] == 2000
        assert 'data' in update_response.data
        assert update_response.data['data']['tags'] == ['新tag1', '新tag2']
        
        # 再次更新：字符串格式
        update_data2 = {
            'tags': '最终tag1,最终tag2,最终tag3'
        }
        
        update_response2 = self.client.patch(f'/api/content/persona/{card_id}/', update_data2, format='json')
        assert update_response2.status_code == status.HTTP_200_OK
        assert update_response2.data['code'] == 2000
        assert 'data' in update_response2.data
        assert update_response2.data['data']['tags'] == ['最终tag1', '最终tag2', '最终tag3']

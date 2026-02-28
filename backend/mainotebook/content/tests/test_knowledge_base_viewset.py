# -*- coding: utf-8 -*-

"""
知识库 ViewSet 测试

测试知识库视图集的基本功能。
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from mainotebook.system.models import Users
from mainotebook.content.models import KnowledgeBase


class KnowledgeBaseViewSetTest(TestCase):
    """知识库 ViewSet 测试类"""
    
    def setUp(self):
        """测试前准备
        
        创建测试用户和 API 客户端。
        """
        # 创建测试用户
        self.user = Users.objects.create_user(
            username='test_user',
            password='test_password',
            name='测试用户'
        )
        
        # 创建 API 客户端
        self.client = APIClient()
        
        # 认证用户
        self.client.force_authenticate(user=self.user)
    
    def test_create_knowledge_base(self):
        """测试创建知识库
        
        验证：
        1. 创建成功返回 201 状态码
        2. 返回的数据包含必填字段
        3. 上传者自动设置为当前用户
        """
        url = '/api/content/knowledge/'
        data = {
            'name': '测试知识库',
            'description': '这是一个测试知识库',
            'version': '1.0'
        }
        
        response = self.client.post(url, data, format='json')
        
        # 验证响应状态码
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证返回数据
        self.assertIn('data', response.data)
        result = response.data['data']
        self.assertEqual(result['name'], '测试知识库')
        self.assertEqual(result['description'], '这是一个测试知识库')
        self.assertEqual(result['uploader'], self.user.id)
    
    def test_list_public_knowledge_bases(self):
        """测试获取公开知识库列表
        
        验证：
        1. 只返回公开且已审核的知识库
        2. 不返回草稿和待审核的知识库
        """
        # 创建公开已审核的知识库
        public_kb = KnowledgeBase.objects.create(
            name='公开知识库',
            description='公开描述',
            uploader=self.user,
            is_public=True,
            is_pending=False
        )
        
        # 创建待审核的知识库
        pending_kb = KnowledgeBase.objects.create(
            name='待审核知识库',
            description='待审核描述',
            uploader=self.user,
            is_public=False,
            is_pending=True
        )
        
        url = '/api/content/knowledge/'
        response = self.client.get(url)
        
        # 验证响应状态码
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证返回数据
        self.assertIn('data', response.data)
        results = response.data['data']
        
        # 应该只包含公开的知识库
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], '公开知识库')
    
    def test_get_my_knowledge_bases(self):
        """测试获取当前用户的知识库列表
        
        验证：
        1. 返回当前用户创建的所有知识库
        2. 包括草稿、待审核、已发布的知识库
        """
        # 创建多个知识库
        kb1 = KnowledgeBase.objects.create(
            name='知识库1',
            description='描述1',
            uploader=self.user,
            is_public=True,
            is_pending=False
        )
        
        kb2 = KnowledgeBase.objects.create(
            name='知识库2',
            description='描述2',
            uploader=self.user,
            is_public=False,
            is_pending=True
        )
        
        url = '/api/content/knowledge/my/'
        response = self.client.get(url)
        
        # 验证响应状态码
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证返回数据
        self.assertIn('data', response.data)
        results = response.data['data']
        
        # 应该包含用户的所有知识库
        self.assertEqual(len(results), 2)
    
    def test_update_knowledge_base_permission(self):
        """测试更新知识库权限
        
        验证：
        1. 创建者可以更新知识库
        2. 非创建者不能更新知识库
        """
        # 创建知识库
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='测试描述',
            uploader=self.user
        )
        
        # 创建另一个用户
        other_user = Users.objects.create_user(
            username='other_user',
            password='test_password',
            name='其他用户'
        )
        
        # 测试创建者可以更新
        url = f'/api/content/knowledge/{kb.id}/'
        data = {'name': '更新后的名称', 'description': '更新后的描述'}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 测试非创建者不能更新
        self.client.force_authenticate(user=other_user)
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_submit_for_review(self):
        """测试提交审核
        
        验证：
        1. 创建者可以提交审核
        2. 提交后状态变为待审核
        """
        # 创建知识库
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='测试描述',
            uploader=self.user,
            is_pending=False
        )
        
        url = f'/api/content/knowledge/{kb.id}/submit/'
        response = self.client.post(url)
        
        # 验证响应状态码
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证知识库状态
        kb.refresh_from_db()
        self.assertTrue(kb.is_pending)
        self.assertFalse(kb.is_public)

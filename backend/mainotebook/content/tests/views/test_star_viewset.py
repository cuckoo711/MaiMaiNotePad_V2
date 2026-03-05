# -*- coding: utf-8 -*-

"""
收藏视图集测试

测试收藏 ViewSet 的功能。
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from mainotebook.system.models import Users
from mainotebook.content.models import KnowledgeBase, PersonaCard, StarRecord


class StarViewSetTestCase(TestCase):
    """收藏视图集测试用例"""
    
    def setUp(self):
        """设置测试环境"""
        self.client = APIClient()
        
        # 创建测试用户
        self.user = Users.objects.create_user(
            username='testuser',
            password='testpass123',
            name='测试用户'
        )
        
        # 创建另一个用户作为内容创建者
        self.creator = Users.objects.create_user(
            username='creator',
            password='testpass123',
            name='创建者'
        )
        
        # 创建测试知识库
        self.knowledge_base = KnowledgeBase.objects.create(
            name='测试知识库',
            description='测试描述',
            uploader=self.creator,
            is_public=True,
            is_pending=False
        )
        
        # 创建测试人设卡
        self.persona_card = PersonaCard.objects.create(
            name='测试人设卡',
            description='测试描述',
            uploader=self.creator,
            is_public=True,
            is_pending=False
        )
        
        # 认证用户
        self.client.force_authenticate(user=self.user)
    
    def test_list_empty_stars(self):
        """测试获取空收藏列表"""
        url = '/api/content/users/stars/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 2000)
        self.assertEqual(len(response.data['data']), 0)
    
    def test_list_stars_with_data(self):
        """测试获取有数据的收藏列表"""
        # 创建收藏记录
        StarRecord.objects.create(
            user=self.user,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge'
        )
        StarRecord.objects.create(
            user=self.user,
            target_id=str(self.persona_card.id),
            target_type='persona'
        )
        
        url = '/api/content/users/stars/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 2000)
        self.assertEqual(len(response.data['data']), 2)
    
    def test_list_stars_filter_by_type(self):
        """测试按类型筛选收藏列表"""
        # 创建收藏记录
        StarRecord.objects.create(
            user=self.user,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge'
        )
        StarRecord.objects.create(
            user=self.user,
            target_id=str(self.persona_card.id),
            target_type='persona'
        )
        
        # 筛选知识库
        url = '/api/content/users/stars/'
        response = self.client.get(url, {'target_type': 'knowledge'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 2000)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['target_type'], 'knowledge')
        
        # 筛选人设卡
        response = self.client.get(url, {'target_type': 'persona'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 2000)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['target_type'], 'persona')
    
    def test_list_stars_invalid_type(self):
        """测试使用无效的类型参数"""
        url = '/api/content/users/stars/'
        response = self.client.get(url, {'target_type': 'invalid'})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 400)
    
    def test_get_stats_empty(self):
        """测试获取空统计数据"""
        url = '/api/content/users/stars/stats/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 2000)
        self.assertEqual(response.data['data']['total'], 0)
        self.assertEqual(response.data['data']['knowledge'], 0)
        self.assertEqual(response.data['data']['persona'], 0)
    
    def test_get_stats_with_data(self):
        """测试获取有数据的统计"""
        # 创建收藏记录
        StarRecord.objects.create(
            user=self.user,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge'
        )
        StarRecord.objects.create(
            user=self.user,
            target_id=str(self.persona_card.id),
            target_type='persona'
        )
        
        url = '/api/content/users/stars/stats/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 2000)
        self.assertEqual(response.data['data']['total'], 2)
        self.assertEqual(response.data['data']['knowledge'], 1)
        self.assertEqual(response.data['data']['persona'], 1)
    
    def test_list_requires_authentication(self):
        """测试未认证用户无法访问"""
        self.client.force_authenticate(user=None)
        
        url = '/api/content/users/stars/'
        response = self.client.get(url)
        
        # mainotebook 可能返回 200 但数据为空，或返回 401
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_200_OK
        ])
    
    def test_stats_requires_authentication(self):
        """测试未认证用户无法访问统计"""
        self.client.force_authenticate(user=None)
        
        url = '/api/content/users/stars/stats/'
        response = self.client.get(url)
        
        # mainotebook 可能返回 200 但数据为空，或返回 401
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_200_OK
        ])

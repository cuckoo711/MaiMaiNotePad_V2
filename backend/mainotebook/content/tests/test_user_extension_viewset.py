# -*- coding: utf-8 -*-

"""
用户扩展视图集测试

测试用户扩展 ViewSet 的功能。
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from mainotebook.system.models import Users
from mainotebook.content.models import (
    KnowledgeBase,
    PersonaCard,
    StarRecord,
    Comment
)


class UserExtensionViewSetTestCase(TestCase):
    """用户扩展视图集测试用例"""
    
    def setUp(self):
        """设置测试环境"""
        self.client = APIClient()
        
        # 创建测试用户
        self.user = Users.objects.create_user(
            username='testuser',
            password='testpass123',
            name='测试用户'
        )
        
        # 创建测试知识库
        self.knowledge_base = KnowledgeBase.objects.create(
            name='测试知识库',
            description='测试描述',
            uploader=self.user,
            is_public=True,
            is_pending=False
        )
        
        # 创建测试人设卡
        self.persona_card = PersonaCard.objects.create(
            name='测试人设卡',
            description='测试描述',
            uploader=self.user,
            is_public=False,
            is_pending=True
        )
        
        # 认证用户
        self.client.force_authenticate(user=self.user)
    
    def test_uploads_list(self):
        """测试获取上传历史"""
        url = reverse('user-extension-uploads')
        response = self.client.get(url)
        
        # 打印响应内容以便调试
        if response.status_code != status.HTTP_200_OK:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.data}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 2000)
        self.assertEqual(len(response.data['data']), 2)
        
        # 验证返回的数据包含必要字段
        upload = response.data['data'][0]
        self.assertIn('id', upload)
        self.assertIn('name', upload)
        self.assertIn('content_type', upload)
        self.assertIn('status', upload)
    
    def test_uploads_filter_by_type(self):
        """测试按类型筛选上传历史"""
        url = reverse('user-extension-uploads')
        response = self.client.get(url, {'content_type': 'knowledge'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['content_type'], 'knowledge')
    
    def test_uploads_filter_by_status(self):
        """测试按状态筛选上传历史"""
        url = reverse('user-extension-uploads')
        response = self.client.get(url, {'status': 'pending'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['status'], 'pending')
    
    def test_stats(self):
        """测试获取上传统计"""
        url = reverse('user-extension-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 2000)
        
        stats = response.data['data']
        self.assertIn('total', stats)
        self.assertIn('knowledge', stats)
        self.assertIn('persona', stats)
        self.assertIn('pass_rate', stats)
        
        # 验证统计数据
        self.assertEqual(stats['total'], 2)
        self.assertEqual(stats['knowledge']['total'], 1)
        self.assertEqual(stats['persona']['total'], 1)
    
    def test_overview(self):
        """测试获取数据概览"""
        # 创建一些测试数据
        StarRecord.objects.create(
            user=self.user,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge'
        )
        
        Comment.objects.create(
            user=self.user,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='测试评论'
        )
        
        url = reverse('user-extension-overview')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 2000)
        
        overview = response.data['data']
        self.assertIn('upload_count', overview)
        self.assertIn('star_count', overview)
        self.assertIn('comment_count', overview)
        self.assertIn('like_count', overview)
        self.assertIn('content_star_count', overview)
        
        # 验证概览数据
        self.assertEqual(overview['upload_count'], 2)
        self.assertEqual(overview['star_count'], 1)
        self.assertEqual(overview['comment_count'], 1)
    
    def test_trend_default(self):
        """测试获取活动趋势（默认参数）"""
        url = reverse('user-extension-trend')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 2000)
        
        # 验证返回的是列表
        self.assertIsInstance(response.data['data'], list)
        
        # 验证趋势数据包含必要字段
        if len(response.data['data']) > 0:
            trend = response.data['data'][0]
            self.assertIn('date', trend)
            self.assertIn('upload_count', trend)
            self.assertIn('comment_count', trend)
            self.assertIn('star_count', trend)
    
    def test_trend_by_week(self):
        """测试按周获取活动趋势"""
        url = reverse('user-extension-trend')
        response = self.client.get(url, {'period': 'week', 'days': 14})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 2000)
    
    def test_trend_by_month(self):
        """测试按月获取活动趋势"""
        url = reverse('user-extension-trend')
        response = self.client.get(url, {'period': 'month', 'days': 60})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 2000)
    
    def test_trend_invalid_period(self):
        """测试无效的时间周期参数"""
        url = reverse('user-extension-trend')
        response = self.client.get(url, {'period': 'invalid'})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_trend_invalid_days(self):
        """测试无效的天数参数"""
        url = reverse('user-extension-trend')
        response = self.client.get(url, {'days': 'invalid'})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_uploads_invalid_type(self):
        """测试无效的内容类型参数"""
        url = reverse('user-extension-uploads')
        response = self.client.get(url, {'content_type': 'invalid'})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_uploads_invalid_status(self):
        """测试无效的状态参数"""
        url = reverse('user-extension-uploads')
        response = self.client.get(url, {'status': 'invalid'})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_unauthenticated_access(self):
        """测试未认证用户访问"""
        self.client.force_authenticate(user=None)
        
        url = reverse('user-extension-uploads')
        response = self.client.get(url)
        
        # mainotebook 框架将认证错误包装在 200 响应中
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 4000)
        self.assertIn('身份认证', response.data['msg'])

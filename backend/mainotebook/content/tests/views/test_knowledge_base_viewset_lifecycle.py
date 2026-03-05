# -*- coding: utf-8 -*-

"""
KnowledgeBase ViewSet 生命周期测试

测试 KnowledgeBase ViewSet 的删除和更新操作中的标签统计同步功能。
"""

import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from mainotebook.system.models import Users
from mainotebook.content.models import KnowledgeBase, TagStatistics


@pytest.mark.django_db
class TestKnowledgeBaseViewSetDestroy(TestCase):
    """测试 KnowledgeBaseViewSet.destroy 方法
    
    验证删除 KnowledgeBase 时标签统计的同步更新。
    Requirements: 2.1
    """
    
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
    
    def test_destroy_public_knowledge_base_decreases_tag_usage(self):
        """测试删除公开 KnowledgeBase 时标签统计减少
        
        验证：
        1. 删除公开的 KnowledgeBase 后，标签统计减少
        2. 物理删除成功
        """
        # 创建公开的 KnowledgeBase
        knowledge_base = KnowledgeBase.objects.create(
            name='测试知识库',
            description='测试描述',
            uploader=self.user,
            is_public=True,
            is_pending=False,
            tags=['机器学习', '深度学习']
        )
        
        # 创建标签统计
        tag_ml = TagStatistics.objects.create(tag='机器学习', tag_type='knowledge', usage_count=10)
        tag_dl = TagStatistics.objects.create(tag='深度学习', tag_type='knowledge', usage_count=8)
        
        # 删除 KnowledgeBase
        url = f'/api/content/knowledge/{knowledge_base.id}/'
        response = self.client.delete(url)
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 验证物理删除
        self.assertFalse(KnowledgeBase.objects.filter(id=knowledge_base.id).exists())
        
        # 验证标签统计减少
        tag_ml.refresh_from_db()
        tag_dl.refresh_from_db()
        self.assertEqual(tag_ml.usage_count, 9)
        self.assertEqual(tag_dl.usage_count, 7)
    
    def test_destroy_private_knowledge_base_no_tag_change(self):
        """测试删除私有 KnowledgeBase 时标签统计不变
        
        验证：
        1. 删除私有的 KnowledgeBase 后，标签统计不变
        2. 物理删除成功
        """
        # 创建私有的 KnowledgeBase
        knowledge_base = KnowledgeBase.objects.create(
            name='私有知识库',
            description='私有描述',
            uploader=self.user,
            is_public=False,
            tags=['数据分析', '可视化']
        )
        
        # 创建标签统计
        tag_analysis = TagStatistics.objects.create(tag='数据分析', tag_type='knowledge', usage_count=6)
        tag_viz = TagStatistics.objects.create(tag='可视化', tag_type='knowledge', usage_count=4)
        
        # 删除 KnowledgeBase
        url = f'/api/content/knowledge/{knowledge_base.id}/'
        response = self.client.delete(url)
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 验证物理删除
        self.assertFalse(KnowledgeBase.objects.filter(id=knowledge_base.id).exists())
        
        # 验证标签统计不变
        tag_analysis.refresh_from_db()
        tag_viz.refresh_from_db()
        self.assertEqual(tag_analysis.usage_count, 6)
        self.assertEqual(tag_viz.usage_count, 4)
    
    def test_destroy_knowledge_base_without_tags(self):
        """测试删除没有标签的 KnowledgeBase
        
        验证：
        1. 删除没有标签的 KnowledgeBase 成功
        2. 不会产生错误
        """
        # 创建没有标签的 KnowledgeBase
        knowledge_base = KnowledgeBase.objects.create(
            name='无标签知识库',
            description='无标签描述',
            uploader=self.user,
            is_public=True,
            is_pending=False,
            tags=[]
        )
        
        # 删除 KnowledgeBase
        url = f'/api/content/knowledge/{knowledge_base.id}/'
        response = self.client.delete(url)
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 验证物理删除
        self.assertFalse(KnowledgeBase.objects.filter(id=knowledge_base.id).exists())
    
    def test_destroy_decreases_usage_count_to_zero(self):
        """测试删除后 usage_count 降为 0 的情况
        
        验证：
        1. 当标签的 usage_count 降为 0 时，TagStatistics 记录被删除
        """
        # 创建公开的 KnowledgeBase
        knowledge_base = KnowledgeBase.objects.create(
            name='稀有标签知识库',
            description='稀有标签描述',
            uploader=self.user,
            is_public=True,
            is_pending=False,
            tags=['罕见标签']
        )
        
        # 创建标签统计（usage_count 为 1）
        tag_rare = TagStatistics.objects.create(tag='罕见标签', tag_type='knowledge', usage_count=1)
        
        # 删除 KnowledgeBase
        url = f'/api/content/knowledge/{knowledge_base.id}/'
        response = self.client.delete(url)
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 验证 TagStatistics 记录被删除
        self.assertFalse(TagStatistics.objects.filter(tag='罕见标签', tag_type='knowledge').exists())


@pytest.mark.django_db
class TestKnowledgeBaseViewSetPerformUpdate(TestCase):
    """测试 KnowledgeBaseViewSet.perform_update 方法
    
    验证更新 KnowledgeBase 时标签统计的同步更新。
    Requirements: 2.4
    
    注意：is_public 状态的切换不通过 PUT 更新，因此只测试标签更新场景。
    """
    
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
    
    def test_update_tags_add_and_remove(self):
        """测试标签列表更新（新增、删除、同时变化）
        
        验证：
        1. 新增标签时，usage_count 增加
        2. 删除标签时，usage_count 减少
        3. 同时新增和删除时，正确处理
        """
        # 创建公开的 KnowledgeBase
        knowledge_base = KnowledgeBase.objects.create(
            name='标签测试知识库',
            description='标签测试描述',
            uploader=self.user,
            is_public=True,
            is_pending=False,
            tags=['旧标签A', '旧标签B']
        )
        
        # 创建标签统计
        tag_old_a = TagStatistics.objects.create(tag='旧标签A', tag_type='knowledge', usage_count=10)
        tag_old_b = TagStatistics.objects.create(tag='旧标签B', tag_type='knowledge', usage_count=8)
        
        # 更新标签：删除 '旧标签B'，添加 '新标签A'，保留 '旧标签A'
        url = f'/api/content/knowledge/{knowledge_base.id}/'
        data = {
            'name': '标签测试知识库',
            'description': '标签测试描述',
            'tags': ['旧标签A', '新标签A']
        }
        response = self.client.put(url, data, format='json')
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证标签统计
        tag_old_a.refresh_from_db()
        tag_old_b.refresh_from_db()
        self.assertEqual(tag_old_a.usage_count, 10)  # 保持不变
        self.assertEqual(tag_old_b.usage_count, 7)  # 减少 1
        
        # 验证新标签创建
        tag_new_a = TagStatistics.objects.get(tag='新标签A', tag_type='knowledge')
        self.assertEqual(tag_new_a.usage_count, 1)
    
    def test_update_tags_no_change(self):
        """测试标签列表没有变化的情况
        
        验证：
        1. 标签列表不变时，标签统计不受影响
        """
        # 创建公开的 KnowledgeBase
        knowledge_base = KnowledgeBase.objects.create(
            name='不变标签知识库',
            description='不变标签描述',
            uploader=self.user,
            is_public=True,
            is_pending=False,
            tags=['标签X', '标签Y']
        )
        
        # 创建标签统计
        tag_x = TagStatistics.objects.create(tag='标签X', tag_type='knowledge', usage_count=12)
        tag_y = TagStatistics.objects.create(tag='标签Y', tag_type='knowledge', usage_count=9)
        
        # 更新其他字段，标签不变
        url = f'/api/content/knowledge/{knowledge_base.id}/'
        data = {
            'name': '更新后的名称',
            'description': '更新后的描述',
            'tags': ['标签X', '标签Y']
        }
        response = self.client.put(url, data, format='json')
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证标签统计不变
        tag_x.refresh_from_db()
        tag_y.refresh_from_db()
        self.assertEqual(tag_x.usage_count, 12)
        self.assertEqual(tag_y.usage_count, 9)
    
    def test_update_non_tag_fields_no_tag_change(self):
        """测试更新非标签字段时标签统计不变
        
        验证：
        1. 只更新 name、description 等非标签字段时，标签统计不受影响
        """
        # 创建公开的 KnowledgeBase
        knowledge_base = KnowledgeBase.objects.create(
            name='原始知识库名称',
            description='原始知识库描述',
            uploader=self.user,
            is_public=True,
            is_pending=False,
            tags=['固定知识标签']
        )
        
        # 创建标签统计
        tag_fixed = TagStatistics.objects.create(tag='固定知识标签', tag_type='knowledge', usage_count=20)
        
        # 只更新 name 和 description
        url = f'/api/content/knowledge/{knowledge_base.id}/'
        data = {
            'name': '新的知识库名称',
            'description': '新的知识库描述',
            'tags': ['固定知识标签']
        }
        response = self.client.put(url, data, format='json')
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证标签统计不变
        tag_fixed.refresh_from_db()
        self.assertEqual(tag_fixed.usage_count, 20)

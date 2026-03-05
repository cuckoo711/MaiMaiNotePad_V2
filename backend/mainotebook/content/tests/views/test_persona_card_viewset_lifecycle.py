# -*- coding: utf-8 -*-

"""
PersonaCard ViewSet 生命周期测试

测试 PersonaCard ViewSet 的删除和更新操作中的标签统计同步功能。
"""

import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from mainotebook.system.models import Users
from mainotebook.content.models import PersonaCard, TagStatistics


@pytest.mark.django_db
class TestPersonaCardViewSetDestroy(TestCase):
    """测试 PersonaCardViewSet.destroy 方法
    
    验证删除 PersonaCard 时标签统计的同步更新。
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
    
    def test_destroy_public_persona_card_decreases_tag_usage(self):
        """测试删除公开 PersonaCard 时标签统计减少
        
        验证：
        1. 删除公开的 PersonaCard 后，标签统计减少
        2. 软删除成功，is_deleted 设置为 True
        """
        # 创建公开的 PersonaCard
        persona_card = PersonaCard.objects.create(
            name='测试人设卡',
            description='测试描述',
            uploader=self.user,
            is_public=True,
            is_pending=False,
            tags=['AI', '助手']
        )
        
        # 创建标签统计
        tag_ai = TagStatistics.objects.create(tag='AI', tag_type='persona', usage_count=5)
        tag_helper = TagStatistics.objects.create(tag='助手', tag_type='persona', usage_count=3)
        
        # 删除 PersonaCard
        url = f'/api/content/persona/{persona_card.id}/'
        response = self.client.delete(url)
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证软删除
        persona_card.refresh_from_db()
        self.assertTrue(persona_card.is_deleted)
        
        # 验证标签统计减少
        tag_ai.refresh_from_db()
        tag_helper.refresh_from_db()
        self.assertEqual(tag_ai.usage_count, 4)
        self.assertEqual(tag_helper.usage_count, 2)

    def test_destroy_private_persona_card_no_tag_change(self):
        """测试删除私有 PersonaCard 时标签统计不变
        
        验证：
        1. 删除私有的 PersonaCard 后，标签统计不变
        2. 软删除成功
        """
        # 创建私有的 PersonaCard
        persona_card = PersonaCard.objects.create(
            name='私有人设卡',
            description='私有描述',
            uploader=self.user,
            is_public=False,
            tags=['游戏', '娱乐']
        )
        
        # 创建标签统计
        tag_game = TagStatistics.objects.create(tag='游戏', tag_type='persona', usage_count=5)
        tag_fun = TagStatistics.objects.create(tag='娱乐', tag_type='persona', usage_count=3)
        
        # 删除 PersonaCard
        url = f'/api/content/persona/{persona_card.id}/'
        response = self.client.delete(url)
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证软删除
        persona_card.refresh_from_db()
        self.assertTrue(persona_card.is_deleted)
        
        # 验证标签统计不变
        tag_game.refresh_from_db()
        tag_fun.refresh_from_db()
        self.assertEqual(tag_game.usage_count, 5)
        self.assertEqual(tag_fun.usage_count, 3)
    
    def test_destroy_persona_card_without_tags(self):
        """测试删除没有标签的 PersonaCard
        
        验证：
        1. 删除没有标签的 PersonaCard 成功
        2. 不会产生错误
        """
        # 创建没有标签的 PersonaCard
        persona_card = PersonaCard.objects.create(
            name='无标签人设卡',
            description='无标签描述',
            uploader=self.user,
            is_public=True,
            is_pending=False,
            tags=[]
        )
        
        # 删除 PersonaCard
        url = f'/api/content/persona/{persona_card.id}/'
        response = self.client.delete(url)
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证软删除
        persona_card.refresh_from_db()
        self.assertTrue(persona_card.is_deleted)
    
    def test_destroy_decreases_usage_count_to_zero(self):
        """测试删除后 usage_count 降为 0 的情况
        
        验证：
        1. 当标签的 usage_count 降为 0 时，TagStatistics 记录被删除
        """
        # 创建公开的 PersonaCard
        persona_card = PersonaCard.objects.create(
            name='稀有标签人设卡',
            description='稀有标签描述',
            uploader=self.user,
            is_public=True,
            is_pending=False,
            tags=['稀有标签']
        )
        
        # 创建标签统计（usage_count 为 1）
        tag_rare = TagStatistics.objects.create(tag='稀有标签', tag_type='persona', usage_count=1)
        
        # 删除 PersonaCard
        url = f'/api/content/persona/{persona_card.id}/'
        response = self.client.delete(url)
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证 TagStatistics 记录被删除
        self.assertFalse(TagStatistics.objects.filter(tag='稀有标签', tag_type='persona').exists())


@pytest.mark.django_db
class TestPersonaCardViewSetPerformUpdate(TestCase):
    """测试 PersonaCardViewSet.perform_update 方法
    
    验证更新 PersonaCard 时标签统计的同步更新。
    Requirements: 2.2, 2.3, 2.4
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
    
    def test_update_public_to_private_decreases_tag_usage(self):
        """测试公开转私有时标签统计减少
        
        验证：
        1. 将 is_public 从 True 改为 False 时，标签统计减少
        
        注意：is_public 状态通过 toggle_public API 切换
        """
        # 创建公开的 PersonaCard
        persona_card = PersonaCard.objects.create(
            name='公开人设卡',
            description='公开描述',
            uploader=self.user,
            is_public=True,
            is_pending=False,
            tags=['Python', 'Django']
        )
        
        # 创建标签统计
        tag_python = TagStatistics.objects.create(tag='Python', tag_type='persona', usage_count=10)
        tag_django = TagStatistics.objects.create(tag='Django', tag_type='persona', usage_count=8)
        
        # 使用 toggle_public API 切换为私有
        url = f'/api/content/persona/{persona_card.id}/toggle-public/'
        response = self.client.post(url)
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证标签统计减少
        tag_python.refresh_from_db()
        tag_django.refresh_from_db()
        self.assertEqual(tag_python.usage_count, 9)
        self.assertEqual(tag_django.usage_count, 7)
    
    def test_update_private_to_public_increases_tag_usage(self):
        """测试私有转公开时标签统计增加
        
        验证：
        1. 将 is_public 从 False 改为 True 时，标签统计增加
        
        注意：is_public 状态通过 toggle_public API 切换
        """
        # 创建私有的 PersonaCard
        persona_card = PersonaCard.objects.create(
            name='私有人设卡',
            description='私有描述',
            uploader=self.user,
            is_public=False,
            tags=['Java', 'Spring']
        )
        
        # 创建标签统计
        tag_java = TagStatistics.objects.create(tag='Java', tag_type='persona', usage_count=5)
        tag_spring = TagStatistics.objects.create(tag='Spring', tag_type='persona', usage_count=3)
        
        # 使用 toggle_public API 切换为公开
        url = f'/api/content/persona/{persona_card.id}/toggle-public/'
        response = self.client.post(url)
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证标签统计增加
        tag_java.refresh_from_db()
        tag_spring.refresh_from_db()
        self.assertEqual(tag_java.usage_count, 6)
        self.assertEqual(tag_spring.usage_count, 4)
    
    def test_update_is_public_no_change(self):
        """测试 is_public 状态没有变化的情况
        
        验证：
        1. is_public 状态不变时，标签统计不受影响
        """
        # 创建公开的 PersonaCard
        persona_card = PersonaCard.objects.create(
            name='测试人设卡',
            description='测试描述',
            uploader=self.user,
            is_public=True,
            is_pending=False,
            tags=['测试']
        )
        
        # 创建标签统计
        tag_test = TagStatistics.objects.create(tag='测试', tag_type='persona', usage_count=5)
        
        # 更新其他字段，is_public 不变
        url = f'/api/content/persona/{persona_card.id}/'
        data = {
            'name': '更新后的名称',
            'description': '更新后的描述',
            'is_public': True,
            'tags': ['测试']
        }
        response = self.client.put(url, data, format='json')
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证标签统计不变
        tag_test.refresh_from_db()
        self.assertEqual(tag_test.usage_count, 5)
    
    def test_update_tags_add_and_remove(self):
        """测试标签列表更新（新增、删除、同时变化）
        
        验证：
        1. 新增标签时，usage_count 增加
        2. 删除标签时，usage_count 减少
        3. 同时新增和删除时，正确处理
        """
        # 创建公开的 PersonaCard
        persona_card = PersonaCard.objects.create(
            name='标签测试人设卡',
            description='标签测试描述',
            uploader=self.user,
            is_public=True,
            is_pending=False,
            tags=['旧标签1', '旧标签2']
        )
        
        # 创建标签统计
        tag_old1 = TagStatistics.objects.create(tag='旧标签1', tag_type='persona', usage_count=5)
        tag_old2 = TagStatistics.objects.create(tag='旧标签2', tag_type='persona', usage_count=3)
        
        # 更新标签：删除 '旧标签2'，添加 '新标签1'，保留 '旧标签1'
        url = f'/api/content/persona/{persona_card.id}/'
        data = {
            'name': '标签测试人设卡',
            'description': '标签测试描述',
            'is_public': True,
            'tags': ['旧标签1', '新标签1']
        }
        response = self.client.put(url, data, format='json')
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证标签统计
        tag_old1.refresh_from_db()
        tag_old2.refresh_from_db()
        self.assertEqual(tag_old1.usage_count, 5)  # 保持不变
        self.assertEqual(tag_old2.usage_count, 2)  # 减少 1
        
        # 验证新标签创建
        tag_new1 = TagStatistics.objects.get(tag='新标签1', tag_type='persona')
        self.assertEqual(tag_new1.usage_count, 1)
    
    def test_update_tags_no_change(self):
        """测试标签列表没有变化的情况
        
        验证：
        1. 标签列表不变时，标签统计不受影响
        """
        # 创建公开的 PersonaCard
        persona_card = PersonaCard.objects.create(
            name='不变标签人设卡',
            description='不变标签描述',
            uploader=self.user,
            is_public=True,
            is_pending=False,
            tags=['标签A', '标签B']
        )
        
        # 创建标签统计
        tag_a = TagStatistics.objects.create(tag='标签A', tag_type='persona', usage_count=5)
        tag_b = TagStatistics.objects.create(tag='标签B', tag_type='persona', usage_count=3)
        
        # 更新其他字段，标签不变
        url = f'/api/content/persona/{persona_card.id}/'
        data = {
            'name': '更新后的名称',
            'description': '更新后的描述',
            'is_public': True,
            'tags': ['标签A', '标签B']
        }
        response = self.client.put(url, data, format='json')
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证标签统计不变
        tag_a.refresh_from_db()
        tag_b.refresh_from_db()
        self.assertEqual(tag_a.usage_count, 5)
        self.assertEqual(tag_b.usage_count, 3)
    
    def test_update_non_tag_fields_no_tag_change(self):
        """测试更新非标签字段时标签统计不变
        
        验证：
        1. 只更新 name、description 等非标签字段时，标签统计不受影响
        """
        # 创建公开的 PersonaCard
        persona_card = PersonaCard.objects.create(
            name='原始名称',
            description='原始描述',
            uploader=self.user,
            is_public=True,
            is_pending=False,
            tags=['固定标签']
        )
        
        # 创建标签统计
        tag_fixed = TagStatistics.objects.create(tag='固定标签', tag_type='persona', usage_count=10)
        
        # 只更新 name 和 description
        url = f'/api/content/persona/{persona_card.id}/'
        data = {
            'name': '新名称',
            'description': '新描述',
            'is_public': True,
            'tags': ['固定标签']
        }
        response = self.client.put(url, data, format='json')
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证标签统计不变
        tag_fixed.refresh_from_db()
        self.assertEqual(tag_fixed.usage_count, 10)

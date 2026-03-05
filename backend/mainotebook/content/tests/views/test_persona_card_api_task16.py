# -*- coding: utf-8 -*-

"""
人设卡状态管理 API 端点测试（任务 16）

测试任务 16 实现的状态管理功能：
- toggle_public: 切换公开/私有状态
- destroy: 软删除人设卡
- 已删除人设卡对其他用户不可见

**验证需求：12.5, 12.6, 12.7, 12.8, 12.10**
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from mainotebook.system.models import Users
from mainotebook.content.models import PersonaCard


class PersonaCardStatusManagementTest(TestCase):
    """人设卡状态管理测试类（任务 16.3）"""
    
    def setUp(self):
        """设置测试环境"""
        self.client = APIClient()
        
        # 创建测试用户
        self.user = Users.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # 创建另一个用户用于权限测试
        self.other_user = Users.objects.create_user(
            username='otheruser',
            password='testpass123',
            email='other@example.com'
        )
        
        # 认证用户
        self.client.force_authenticate(user=self.user)
        
        # 设置默认的 HTTP_USER_AGENT 头
        self.client.defaults['HTTP_USER_AGENT'] = 'Mozilla/5.0 (Test Client)'
    
    def test_toggle_public_to_private(self):
        """测试公开转私有（任务 16.3）
        
        验证需求：12.5, 12.6
        属性 43: 公开转私有状态转换
        属性 44: 公开转私有审核状态重置
        """
        # 创建一个公开且已通过审核的人设卡
        persona_card = PersonaCard.objects.create(
            name='公开人设卡',
            description='这是一个公开的人设卡',
            uploader=self.user,
            is_public=True,
            is_pending=False,  # 已通过审核
            creator=self.user,
            modifier=self.user.username
        )
        
        # 发送切换请求
        url = f'/api/content/persona/{persona_card.id}/toggle-public/'
        response = self.client.post(url)
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('已将人设卡设为私有', response.data.get('msg', ''))
        
        # 验证数据库状态
        persona_card.refresh_from_db()
        self.assertFalse(persona_card.is_public)  # 应该变为私有
        self.assertFalse(persona_card.is_pending)  # 保持 False（需求 12.6）
    
    def test_toggle_private_to_public(self):
        """测试私有转公开（触发审核）（任务 16.3）
        
        验证需求：12.7
        属性 45: 私有转公开重新审核
        """
        # 创建一个私有人设卡
        persona_card = PersonaCard.objects.create(
            name='私有人设卡',
            description='这是一个私有的人设卡',
            uploader=self.user,
            is_public=False,
            is_pending=False,
            creator=self.user,
            modifier=self.user.username
        )
        
        # 发送切换请求
        url = f'/api/content/persona/{persona_card.id}/toggle-public/'
        response = self.client.post(url)
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('正在审核中', response.data.get('msg', ''))
        
        # 验证数据库状态
        persona_card.refresh_from_db()
        self.assertTrue(persona_card.is_public)  # 应该变为公开
        self.assertTrue(persona_card.is_pending)  # 应该触发审核（需求 12.7）
    
    def test_toggle_public_permission_denied(self):
        """测试非上传者无法切换状态（任务 16.3）
        
        验证需求：12.5
        """
        # 创建一个人设卡
        persona_card = PersonaCard.objects.create(
            name='测试人设卡',
            description='这是一个测试人设卡',
            uploader=self.user,
            is_public=False,
            is_pending=False,
            creator=self.user,
            modifier=self.user.username
        )
        
        # 切换到另一个用户
        self.client.force_authenticate(user=self.other_user)
        
        # 发送切换请求
        url = f'/api/content/persona/{persona_card.id}/toggle-public/'
        response = self.client.post(url)
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('只有上传者可以切换人设卡状态', response.data.get('msg', ''))
    
    def test_soft_delete_persona_card(self):
        """测试软删除人设卡（任务 16.3）
        
        验证需求：12.8, 12.9
        属性 46: 软删除人设卡
        """
        # 创建一个人设卡
        persona_card = PersonaCard.objects.create(
            name='待删除人设卡',
            description='这是一个待删除的人设卡',
            uploader=self.user,
            is_public=False,
            is_pending=False,
            creator=self.user,
            modifier=self.user.username
        )
        
        persona_card_id = persona_card.id
        
        # 发送删除请求
        url = f'/api/content/persona/{persona_card_id}/'
        response = self.client.delete(url)
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('删除成功', response.data.get('msg', ''))
        
        # 验证数据库状态：记录仍然存在（软删除）
        persona_card = PersonaCard.objects.get(id=persona_card_id)
        self.assertTrue(persona_card.is_deleted)  # 应该标记为已删除
        
        # 验证数据库完整性（需求 12.9）
        self.assertIsNotNone(persona_card)
        self.assertEqual(persona_card.name, '待删除人设卡')
    
    def test_soft_delete_permission_denied(self):
        """测试非上传者无法删除人设卡（任务 16.3）
        
        验证需求：12.8
        """
        # 创建一个人设卡
        persona_card = PersonaCard.objects.create(
            name='测试人设卡',
            description='这是一个测试人设卡',
            uploader=self.user,
            is_public=False,
            is_pending=False,
            creator=self.user,
            modifier=self.user.username
        )
        
        # 切换到另一个用户
        self.client.force_authenticate(user=self.other_user)
        
        # 发送删除请求
        url = f'/api/content/persona/{persona_card.id}/'
        response = self.client.delete(url)
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('只有上传者可以删除人设卡', response.data.get('msg', ''))
    
    def test_deleted_persona_card_hidden_from_others(self):
        """测试已删除人设卡对其他用户不可见（任务 16.3）
        
        验证需求：12.10
        属性 47: 已删除人设卡隐藏
        """
        # 创建一个公开的人设卡
        persona_card = PersonaCard.objects.create(
            name='公开人设卡',
            description='这是一个公开的人设卡',
            uploader=self.user,
            is_public=True,
            is_pending=False,
            creator=self.user,
            modifier=self.user.username
        )
        
        # 软删除人设卡
        persona_card.is_deleted = True
        persona_card.save()
        
        # 切换到另一个用户
        self.client.force_authenticate(user=self.other_user)
        
        # 尝试获取人设卡列表
        url = '/api/content/persona/'
        response = self.client.get(url)
        
        # 验证响应：已删除的人设卡不应该出现在列表中
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 响应数据可能是列表或包含 data/results 的字典
        if isinstance(response.data, list):
            results = response.data
        elif isinstance(response.data, dict):
            if 'data' in response.data and isinstance(response.data['data'], dict):
                results = response.data['data'].get('results', [])
            elif 'results' in response.data:
                results = response.data['results']
            else:
                results = []
        else:
            results = []
        
        # 确保已删除的人设卡不在列表中
        persona_card_ids = [item.get('id') if isinstance(item, dict) else str(item) for item in results]
        self.assertNotIn(str(persona_card.id), persona_card_ids)
    
    def test_deleted_persona_card_not_retrievable_by_others(self):
        """测试其他用户无法查看已删除的人设卡详情（任务 16.3）
        
        验证需求：12.10
        """
        # 创建一个公开的人设卡
        persona_card = PersonaCard.objects.create(
            name='公开人设卡',
            description='这是一个公开的人设卡',
            uploader=self.user,
            is_public=True,
            is_pending=False,
            creator=self.user,
            modifier=self.user.username
        )
        
        # 软删除人设卡
        persona_card.is_deleted = True
        persona_card.save()
        
        # 切换到另一个用户
        self.client.force_authenticate(user=self.other_user)
        
        # 尝试获取人设卡详情
        url = f'/api/content/persona/{persona_card.id}/'
        response = self.client.get(url)
        
        # 验证响应：应该返回 404（因为查询集中已过滤）
        # 由于我们修改了 get_queryset，已删除的人设卡对其他用户不可见
        # 如果返回 200，检查是否真的返回了数据
        if response.status_code == status.HTTP_200_OK:
            # 如果返回 200，数据应该为空或不包含该人设卡
            response_data = response.data.get('data', response.data) if isinstance(response.data, dict) else response.data
            if response_data and isinstance(response_data, dict):
                # 如果有数据，确保不是我们要找的人设卡
                self.assertNotEqual(response_data.get('id'), str(persona_card.id))
        else:
            # 应该返回 404
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_owner_can_view_deleted_persona_card(self):
        """测试上传者可以查看自己已删除的人设卡（任务 16.3）
        
        验证需求：12.10
        """
        # 创建一个人设卡
        persona_card = PersonaCard.objects.create(
            name='我的人设卡',
            description='这是我的人设卡',
            uploader=self.user,
            is_public=False,
            is_pending=False,
            creator=self.user,
            modifier=self.user.username
        )
        
        # 软删除人设卡
        persona_card.is_deleted = True
        persona_card.save()
        
        # 上传者尝试获取人设卡详情
        url = f'/api/content/persona/{persona_card.id}/'
        response = self.client.get(url)
        
        # 验证响应：上传者应该能看到（用于管理）
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 响应数据可能直接是数据对象或包含在 data 字段中
        if isinstance(response.data, dict):
            response_data = response.data.get('data', response.data)
            if response_data and isinstance(response_data, dict):
                self.assertEqual(response_data.get('id'), str(persona_card.id))
            else:
                # 如果 response_data 为 None 或不是字典，检查原始 response.data
                self.assertEqual(response.data.get('id'), str(persona_card.id))

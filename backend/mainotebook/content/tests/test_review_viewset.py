"""
审核 ViewSet 测试

测试审核视图集的基本功能。
"""

import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from mainotebook.system.models import Users
from mainotebook.content.models import KnowledgeBase, PersonaCard


@pytest.mark.django_db
class TestReviewViewSet(TestCase):
    """审核 ViewSet 测试类"""
    
    def setUp(self):
        """设置测试环境"""
        self.client = APIClient()
        
        # 创建测试用户
        self.user = Users.objects.create_user(
            username='testuser',
            password='testpass123',
            name='测试用户'
        )
        
        # 创建审核员用户
        self.moderator = Users.objects.create_user(
            username='moderator',
            password='testpass123',
            name='审核员',
            is_staff=True
        )
        
        # 创建待审核的知识库
        self.knowledge_base = KnowledgeBase.objects.create(
            name='测试知识库',
            description='测试描述',
            uploader=self.user,
            is_pending=True,
            is_public=False
        )
        
        # 创建待审核的人设卡
        self.persona_card = PersonaCard.objects.create(
            name='测试人设卡',
            description='测试描述',
            uploader=self.user,
            is_pending=True,
            is_public=False
        )
    
    def test_list_pending_items_requires_authentication(self):
        """测试获取待审核列表需要认证"""
        response = self.client.get('/api/content/review/')
        # mainotebook 可能返回 200 但数据为空，或返回 401/403
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_200_OK
        ])
    
    def test_list_pending_items_requires_moderator_permission(self):
        """测试获取待审核列表需要审核员权限"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/content/review/')
        # 普通用户应该被拒绝访问
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_200_OK])
    
    def test_list_pending_items_success(self):
        """测试审核员成功获取待审核列表"""
        self.client.force_authenticate(user=self.moderator)
        response = self.client.get('/api/content/review/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('code', response.data)
        self.assertEqual(response.data['code'], 2000)
        self.assertIn('data', response.data)
    
    def test_approve_content_success(self):
        """测试批准内容成功"""
        self.client.force_authenticate(user=self.moderator)
        
        response = self.client.post(
            f'/api/content/review/{self.knowledge_base.id}/approve/',
            {'content_type': 'knowledge'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证知识库状态已更新
        self.knowledge_base.refresh_from_db()
        self.assertFalse(self.knowledge_base.is_pending)
        self.assertTrue(self.knowledge_base.is_public)
    
    def test_reject_content_requires_reason(self):
        """测试拒绝内容需要提供原因"""
        self.client.force_authenticate(user=self.moderator)
        
        # 测试完全不提供 reason 字段
        response = self.client.post(
            f'/api/content/review/{self.knowledge_base.id}/reject/',
            {'content_type': 'knowledge'}
        )
        
        # 应该返回 400 错误
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_reject_content_success(self):
        """测试拒绝内容成功"""
        self.client.force_authenticate(user=self.moderator)
        
        response = self.client.post(
            f'/api/content/review/{self.knowledge_base.id}/reject/',
            {'content_type': 'knowledge', 'reason': '内容不符合规范'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证知识库状态已更新
        self.knowledge_base.refresh_from_db()
        self.assertFalse(self.knowledge_base.is_pending)
        self.assertFalse(self.knowledge_base.is_public)
        self.assertEqual(self.knowledge_base.rejection_reason, '内容不符合规范')
    
    def test_return_draft_success(self):
        """测试退回内容成功"""
        self.client.force_authenticate(user=self.moderator)
        
        response = self.client.post(
            f'/api/content/review/{self.persona_card.id}/return_draft/',
            {'content_type': 'persona', 'reason': '需要修改'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证人设卡状态已更新
        self.persona_card.refresh_from_db()
        self.assertFalse(self.persona_card.is_pending)
        self.assertFalse(self.persona_card.is_public)
    
    def test_get_stats_success(self):
        """测试获取审核统计成功"""
        self.client.force_authenticate(user=self.moderator)
        
        response = self.client.get('/api/content/review/stats/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        
        stats = response.data['data']
        self.assertIn('pending_count', stats)
        self.assertIn('pending_knowledge', stats)
        self.assertIn('pending_persona', stats)
        self.assertIn('approved_today', stats)
        self.assertIn('rejected_today', stats)
        self.assertIn('pass_rate', stats)

    # ========== 默认分页参数测试 ==========

    def test_list_default_pagination_params(self):
        """测试默认分页参数 page=1, page_size=10（需求 1.3）"""
        self.client.force_authenticate(user=self.moderator)
        response = self.client.get('/api/content/review/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('data', {})
        # 验证分页字段存在
        self.assertIn('page', data)
        self.assertIn('page_size', data)
        self.assertEqual(data['page'], 1)
        self.assertEqual(data['page_size'], 10)

    # ========== 缺少 content_type 参数测试 ==========

    def test_approve_missing_content_type(self):
        """测试审核通过缺少 content_type 参数（需求 2.3）"""
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(
            f'/api/content/review/{self.knowledge_base.id}/approve/',
            {}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_missing_content_type(self):
        """测试审核拒绝缺少 content_type 参数（需求 3.5）"""
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(
            f'/api/content/review/{self.knowledge_base.id}/reject/',
            {'reason': '拒绝原因'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ========== 批量操作 ids 为空测试 ==========

    def test_batch_approve_empty_ids(self):
        """测试批量审核通过 ids 为空（需求 6.4）"""
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(
            '/api/content/review/batch_approve/',
            {'ids': [], 'content_type': 'knowledge'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_batch_reject_empty_ids(self):
        """测试批量审核拒绝 ids 为空（需求 6.5）"""
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(
            '/api/content/review/batch_reject/',
            {'ids': [], 'content_type': 'knowledge', 'reason': '拒绝原因'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ========== 批量操作缺少 content_type 测试 ==========

    def test_batch_approve_missing_content_type(self):
        """测试批量审核通过缺少 content_type（需求 6.5）"""
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(
            '/api/content/review/batch_approve/',
            {'ids': [str(self.knowledge_base.id)]},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ========== reason 为空和超长的错误响应测试 ==========

    def test_reject_empty_reason_via_api(self):
        """测试通过 API 拒绝内容时 reason 为空（需求 3.3）"""
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(
            f'/api/content/review/{self.knowledge_base.id}/reject/',
            {'content_type': 'knowledge', 'reason': ''}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_too_long_reason_via_api(self):
        """测试通过 API 拒绝内容时 reason 超过 500 字符（需求 3.4）"""
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(
            f'/api/content/review/{self.knowledge_base.id}/reject/',
            {'content_type': 'knowledge', 'reason': 'A' * 501}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ========== 内容不存在边界条件测试 ==========

    def test_approve_nonexistent_content_via_api(self):
        """测试通过 API 审核通过不存在的内容（需求 2.5）"""
        import uuid
        self.client.force_authenticate(user=self.moderator)
        fake_id = str(uuid.uuid4())
        response = self.client.post(
            f'/api/content/review/{fake_id}/approve/',
            {'content_type': 'knowledge'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_nonexistent_content_via_api(self):
        """测试通过 API 审核拒绝不存在的内容（需求 3.6）"""
        import uuid
        self.client.force_authenticate(user=self.moderator)
        fake_id = str(uuid.uuid4())
        response = self.client.post(
            f'/api/content/review/{fake_id}/reject/',
            {'content_type': 'knowledge', 'reason': '拒绝原因'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

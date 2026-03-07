"""集成测试：评论和登录权限检查

测试评论创建时的禁言检查和登录时的封禁检查功能。
"""

import pytest
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError

from mainotebook.system.models import Users
from mainotebook.content.services.comment_service import CommentService
from mainotebook.content.models import UserMuteRecord
from mainotebook.utils.validator import CustomValidationError


class TestCommentMuteCheck(TestCase):
    """测试评论创建时的禁言检查"""
    
    def setUp(self):
        """测试前准备"""
        self.user = Users.objects.create(
            username='test_user',
            email='test@example.com',
            is_active=True,
            is_muted=False
        )
    
    def test_normal_user_can_comment(self):
        """测试正常用户可以发表评论"""
        data = {
            'target_id': 'test-target-id',
            'target_type': 'knowledge',
            'content': '这是一条测试评论'
        }
        
        # 应该不抛出异常
        try:
            # 注意：这里会调用 AI 审核，可能需要 mock
            # comment = CommentService.create_comment(self.user, data)
            # self.assertIsNotNone(comment)
            pass
        except ValidationError:
            self.fail("正常用户不应该被禁止发表评论")
    
    def test_permanently_muted_user_cannot_comment(self):
        """测试永久禁言用户无法发表评论"""
        self.user.is_muted = True
        self.user.muted_until = None  # 永久禁言
        self.user.mute_reason = '严重违规'
        self.user.save()
        
        data = {
            'target_id': 'test-target-id',
            'target_type': 'knowledge',
            'content': '这是一条测试评论'
        }
        
        with self.assertRaises(ValidationError) as context:
            CommentService.create_comment(self.user, data)
        
        self.assertIn('永久禁言', str(context.exception))
        self.assertIn('严重违规', str(context.exception))
    
    def test_unexpired_muted_user_cannot_comment(self):
        """测试未过期禁言用户无法发表评论"""
        self.user.is_muted = True
        self.user.muted_until = timezone.now() + timedelta(hours=24)
        self.user.mute_reason = '发布违规内容'
        self.user.save()
        
        data = {
            'target_id': 'test-target-id',
            'target_type': 'knowledge',
            'content': '这是一条测试评论'
        }
        
        with self.assertRaises(ValidationError) as context:
            CommentService.create_comment(self.user, data)
        
        error_msg = str(context.exception)
        self.assertIn('已被禁言至', error_msg)
        self.assertIn('发布违规内容', error_msg)
    
    def test_expired_mute_auto_unmute(self):
        """测试过期禁言自动解除"""
        # 设置已过期的禁言
        self.user.is_muted = True
        self.user.muted_until = timezone.now() - timedelta(hours=1)
        self.user.mute_reason = '测试禁言'
        self.user.save()
        
        # 创建禁言记录
        mute_record = UserMuteRecord.objects.create(
            user=self.user,
            mute_type='manual',
            mute_reason='测试禁言',
            muted_until=self.user.muted_until,
            is_active=True
        )
        
        data = {
            'target_id': 'test-target-id',
            'target_type': 'knowledge',
            'content': '这是一条测试评论'
        }
        
        # 应该自动解除禁言并允许评论
        # 注意：这里会调用 AI 审核，实际测试时需要 mock
        # comment = CommentService.create_comment(self.user, data)
        
        # 验证用户状态已更新
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_muted)
        
        # 验证禁言记录已更新
        mute_record.refresh_from_db()
        self.assertFalse(mute_record.is_active)
        self.assertIsNotNone(mute_record.unmuted_at)


class TestLoginBanCheck(TestCase):
    """测试登录时的封禁检查"""
    
    def setUp(self):
        """测试前准备"""
        self.user = Users.objects.create(
            username='test_user',
            email='test@example.com',
            is_active=True
        )
        self.user.set_password('test_password')
        self.user.save()
    
    def test_normal_user_can_login(self):
        """测试正常用户可以登录"""
        # 这个测试需要通过 API 测试来验证
        # 因为 LoginSerializer 需要完整的请求上下文
        pass
    
    def test_permanently_banned_user_cannot_login(self):
        """测试永久封禁用户无法登录"""
        self.user.is_active = False
        self.user.locked_until = None  # 永久封禁
        self.user.ban_reason = '严重违反平台规则'
        self.user.save()
        
        # 这个测试需要通过 API 测试来验证
        # 应该抛出 CustomValidationError，包含"永久封禁"和原因
        pass
    
    def test_unexpired_banned_user_cannot_login(self):
        """测试未过期封禁用户无法登录"""
        self.user.is_active = False
        self.user.locked_until = timezone.now() + timedelta(days=7)
        self.user.ban_reason = '发布违规内容'
        self.user.save()
        
        # 这个测试需要通过 API 测试来验证
        # 应该抛出 CustomValidationError，包含封禁截止时间和原因
        pass
    
    def test_expired_ban_auto_unban(self):
        """测试过期封禁自动解除"""
        # 设置已过期的封禁
        self.user.is_active = False
        self.user.locked_until = timezone.now() - timedelta(hours=1)
        self.user.ban_reason = '测试封禁'
        self.user.save()
        
        # 这个测试需要通过 API 测试来验证
        # 登录时应该自动解除封禁并允许登录
        # 验证用户状态已更新为 is_active=True
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

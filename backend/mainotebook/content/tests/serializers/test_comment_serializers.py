# -*- coding: utf-8 -*-

"""
评论序列化器测试

测试评论序列化器的数据验证、树形结构序列化功能。

验证需求：4.1, 4.11, 4.12, 10.3
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIRequestFactory
from mainotebook.system.models import Users
from mainotebook.content.models import Comment, CommentReaction, KnowledgeBase
from mainotebook.content.serializers.comment import (
    CommentSerializer,
    CommentCreateSerializer,
)


class TestCommentSerializer(TestCase):
    """测试评论序列化器"""
    
    def setUp(self):
        """测试前准备"""
        self.factory = APIRequestFactory()
        self.user = Users.objects.create(
            username="testuser",
            name="测试用户",
            email="test@example.com",
            avatar="avatar.jpg"
        )
        self.kb = KnowledgeBase.objects.create(
            name="测试知识库",
            description="测试描述",
            uploader=self.user
        )
    
    def tearDown(self):
        """测试后清理"""
        CommentReaction.objects.all().delete()
        Comment.objects.all().delete()
        KnowledgeBase.objects.all().delete()
        Users.objects.all().delete()
    
    def test_serialize_comment(self):
        """测试评论序列化（需求 10.3）"""
        comment = Comment.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            content="这是一条测试评论"
        )
        
        request = self.factory.get('/')
        request.user = self.user
        
        serializer = CommentSerializer(comment, context={'request': request})
        data = serializer.data
        
        # 验证基本字段
        self.assertEqual(data['content'], "这是一条测试评论")
        self.assertEqual(data['user_name'], "测试用户")
        self.assertEqual(data['user_avatar'], "avatar.jpg")
        self.assertEqual(data['target_id'], str(self.kb.id))
        self.assertEqual(data['target_type'], 'knowledge')
        self.assertFalse(data['is_deleted'])
        self.assertEqual(data['like_count'], 0)
        self.assertEqual(data['dislike_count'], 0)
        
        # 验证关联字段
        self.assertIn('replies', data)
        self.assertIn('is_liked', data)
        self.assertFalse(data['is_liked'])
    
    def test_serialize_comment_with_replies(self):
        """测试评论树形结构序列化（需求 4.11, 4.12）"""
        # 创建父评论
        parent_comment = Comment.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            content="父评论"
        )
        
        # 创建子评论
        child_comment1 = Comment.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            parent=parent_comment,
            content="子评论1"
        )
        child_comment2 = Comment.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            parent=parent_comment,
            content="子评论2"
        )
        
        # 创建孙评论
        grandchild_comment = Comment.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            parent=child_comment1,
            content="孙评论"
        )
        
        request = self.factory.get('/')
        request.user = self.user
        
        serializer = CommentSerializer(parent_comment, context={'request': request})
        data = serializer.data
        
        # 验证父评论
        self.assertEqual(data['content'], "父评论")
        self.assertIn('replies', data)
        self.assertEqual(len(data['replies']), 2)
        
        # 验证子评论
        reply_contents = [reply['content'] for reply in data['replies']]
        self.assertIn("子评论1", reply_contents)
        self.assertIn("子评论2", reply_contents)
        
        # 验证孙评论（嵌套结构）
        child1_data = next(r for r in data['replies'] if r['content'] == "子评论1")
        self.assertEqual(len(child1_data['replies']), 1)
        self.assertEqual(child1_data['replies'][0]['content'], "孙评论")
    
    def test_serialize_comment_with_deleted_replies(self):
        """测试序列化时过滤已删除的回复（需求 4.11）"""
        # 创建父评论
        parent_comment = Comment.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            content="父评论"
        )
        
        # 创建正常子评论
        Comment.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            parent=parent_comment,
            content="正常子评论"
        )
        
        # 创建已删除的子评论
        Comment.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            parent=parent_comment,
            content="已删除子评论",
            is_deleted=True
        )
        
        request = self.factory.get('/')
        request.user = self.user
        
        serializer = CommentSerializer(parent_comment, context={'request': request})
        data = serializer.data
        
        # 验证只包含未删除的回复
        self.assertEqual(len(data['replies']), 1)
        self.assertEqual(data['replies'][0]['content'], "正常子评论")
    
    def test_get_is_liked_authenticated_user(self):
        """测试已认证用户的点赞状态"""
        comment = Comment.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            content="测试评论"
        )
        
        # 创建点赞记录
        CommentReaction.objects.create(
            user=self.user,
            comment=comment,
            reaction_type='like'
        )
        
        request = self.factory.get('/')
        request.user = self.user
        
        serializer = CommentSerializer(comment, context={'request': request})
        data = serializer.data
        
        # 验证点赞状态
        self.assertTrue(data['is_liked'])
    
    def test_get_is_liked_not_liked(self):
        """测试未点赞的状态"""
        comment = Comment.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            content="测试评论"
        )
        
        request = self.factory.get('/')
        request.user = self.user
        
        serializer = CommentSerializer(comment, context={'request': request})
        data = serializer.data
        
        # 验证未点赞状态
        self.assertFalse(data['is_liked'])
    
    def test_get_is_liked_unauthenticated_user(self):
        """测试未认证用户的点赞状态"""
        from django.contrib.auth.models import AnonymousUser
        
        comment = Comment.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            content="测试评论"
        )
        
        request = self.factory.get('/')
        request.user = AnonymousUser()
        
        serializer = CommentSerializer(comment, context={'request': request})
        data = serializer.data
        
        # 验证未认证用户的点赞状态为 False
        self.assertFalse(data['is_liked'])
    
    def test_read_only_fields(self):
        """测试只读字段"""
        serializer = CommentSerializer()
        read_only_fields = serializer.Meta.read_only_fields
        
        self.assertIn('id', read_only_fields)
        self.assertIn('like_count', read_only_fields)
        self.assertIn('dislike_count', read_only_fields)
        self.assertIn('create_datetime', read_only_fields)
        self.assertIn('update_datetime', read_only_fields)
        self.assertIn('user', read_only_fields)


class TestCommentCreateSerializer(TestCase):
    """测试评论创建序列化器"""
    
    def setUp(self):
        """测试前准备"""
        self.factory = APIRequestFactory()
        self.user = Users.objects.create(
            username="testuser",
            name="测试用户",
            email="test@example.com"
        )
        self.kb = KnowledgeBase.objects.create(
            name="测试知识库",
            description="测试描述",
            uploader=self.user
        )
    
    def tearDown(self):
        """测试后清理"""
        Comment.objects.all().delete()
        KnowledgeBase.objects.all().delete()
        Users.objects.all().delete()
    
    def test_create_with_valid_data(self):
        """测试使用有效数据创建评论（需求 4.1）"""
        request = self.factory.post('/')
        request.user = self.user
        
        data = {
            'target_id': str(self.kb.id),
            'target_type': 'knowledge',
            'content': '这是一条测试评论'
        }
        
        serializer = CommentCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        comment = serializer.save()
        
        # 验证创建成功
        self.assertEqual(comment.content, '这是一条测试评论')
        self.assertEqual(comment.user, self.user)
        self.assertEqual(comment.target_id, str(self.kb.id))
        self.assertEqual(comment.target_type, 'knowledge')
        self.assertIsNone(comment.parent)
    
    def test_create_reply_with_parent(self):
        """测试创建回复评论（需求 4.1）"""
        # 创建父评论
        parent_comment = Comment.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            content="父评论"
        )
        
        request = self.factory.post('/')
        request.user = self.user
        
        data = {
            'target_id': str(self.kb.id),
            'target_type': 'knowledge',
            'parent': parent_comment.id,
            'content': '这是一条回复'
        }
        
        serializer = CommentCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        comment = serializer.save()
        
        # 验证回复创建成功
        self.assertEqual(comment.content, '这是一条回复')
        self.assertEqual(comment.parent, parent_comment)
    
    def test_validate_content_empty(self):
        """测试验证空内容（需求 4.1）"""
        request = self.factory.post('/')
        request.user = self.user
        
        data = {
            'target_id': str(self.kb.id),
            'target_type': 'knowledge',
            'content': ''
        }
        
        serializer = CommentCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        # 验证失败（字段名可能是中文或英文）
        self.assertFalse(serializer.is_valid())
        self.assertTrue('content' in serializer.errors or '评论内容' in serializer.errors)
    
    def test_validate_content_whitespace_only(self):
        """测试验证仅包含空白字符的内容（需求 4.1）"""
        request = self.factory.post('/')
        request.user = self.user
        
        data = {
            'target_id': str(self.kb.id),
            'target_type': 'knowledge',
            'content': '   \n\t  '
        }
        
        serializer = CommentCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        # 验证失败（字段名可能是中文或英文）
        self.assertFalse(serializer.is_valid())
        self.assertTrue('content' in serializer.errors or '评论内容' in serializer.errors)
    
    def test_validate_content_max_length(self):
        """测试验证内容长度限制（需求 4.1）"""
        request = self.factory.post('/')
        request.user = self.user
        
        # 创建超过 500 字符的内容
        long_content = 'a' * 501
        
        data = {
            'target_id': str(self.kb.id),
            'target_type': 'knowledge',
            'content': long_content
        }
        
        serializer = CommentCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        # 验证失败（字段名可能是中文或英文）
        self.assertFalse(serializer.is_valid())
        self.assertTrue('content' in serializer.errors or '评论内容' in serializer.errors)
        # 验证错误消息包含 500
        error_messages = str(serializer.errors)
        self.assertTrue('500' in error_messages)
    
    def test_validate_content_exactly_500_chars(self):
        """测试验证恰好 500 字符的内容（需求 4.1）"""
        request = self.factory.post('/')
        request.user = self.user
        
        # 创建恰好 500 字符的内容
        content = 'a' * 500
        
        data = {
            'target_id': str(self.kb.id),
            'target_type': 'knowledge',
            'content': content
        }
        
        serializer = CommentCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        # 验证成功
        self.assertTrue(serializer.is_valid(), serializer.errors)
    
    def test_validate_parent_deleted(self):
        """测试验证已删除的父评论（需求 4.1）"""
        # 创建已删除的父评论
        parent_comment = Comment.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            content="已删除的父评论",
            is_deleted=True
        )
        
        request = self.factory.post('/')
        request.user = self.user
        
        data = {
            'target_id': str(self.kb.id),
            'target_type': 'knowledge',
            'parent': parent_comment.id,
            'content': '回复已删除的评论'
        }
        
        serializer = CommentCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        # 验证失败（字段名可能是中文或英文）
        self.assertFalse(serializer.is_valid())
        self.assertTrue('parent' in serializer.errors or '父评论' in serializer.errors)
    
    def test_validate_parent_not_exists(self):
        """测试验证不存在的父评论（需求 4.1）"""
        request = self.factory.post('/')
        request.user = self.user
        
        # 使用不存在的 UUID
        import uuid
        non_existent_id = uuid.uuid4()
        
        data = {
            'target_id': str(self.kb.id),
            'target_type': 'knowledge',
            'parent': non_existent_id,
            'content': '回复不存在的评论'
        }
        
        serializer = CommentCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        # 验证失败（DRF 会在字段级别验证失败）
        self.assertFalse(serializer.is_valid())
    
    def test_validate_muted_user(self):
        """测试验证被禁言的用户（需求 4.1）"""
        # 设置用户为禁言状态
        self.user.is_muted = True
        self.user.muted_until = timezone.now() + timedelta(days=1)
        self.user.save()
        
        request = self.factory.post('/')
        request.user = self.user
        
        data = {
            'target_id': str(self.kb.id),
            'target_type': 'knowledge',
            'content': '被禁言用户的评论'
        }
        
        serializer = CommentCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        # 验证失败
        self.assertFalse(serializer.is_valid())
        self.assertTrue(any('禁言' in str(e) for e in serializer.errors.get('non_field_errors', [])))
    
    def test_validate_muted_user_expired(self):
        """测试验证禁言已过期的用户（需求 4.1）"""
        # 设置用户为禁言状态，但已过期
        self.user.is_muted = True
        self.user.muted_until = timezone.now() - timedelta(days=1)
        self.user.save()
        
        request = self.factory.post('/')
        request.user = self.user
        
        data = {
            'target_id': str(self.kb.id),
            'target_type': 'knowledge',
            'content': '禁言已过期用户的评论'
        }
        
        serializer = CommentCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        # 验证成功（禁言已过期）
        self.assertTrue(serializer.is_valid(), serializer.errors)
    
    def test_auto_set_user(self):
        """测试自动设置评论用户（需求 4.1）"""
        request = self.factory.post('/')
        request.user = self.user
        
        data = {
            'target_id': str(self.kb.id),
            'target_type': 'knowledge',
            'content': '测试评论'
        }
        
        serializer = CommentCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        comment = serializer.save()
        
        # 验证用户自动设置
        self.assertEqual(comment.user, self.user)
    
    def test_validate_without_request_context(self):
        """测试缺少请求上下文时的验证"""
        data = {
            'target_id': str(self.kb.id),
            'target_type': 'knowledge',
            'content': '测试评论'
        }
        
        serializer = CommentCreateSerializer(data=data, context={})
        
        # 验证失败
        self.assertFalse(serializer.is_valid())
    
    def test_validate_unauthenticated_user(self):
        """测试未认证用户的验证"""
        from django.contrib.auth.models import AnonymousUser
        
        request = self.factory.post('/')
        request.user = AnonymousUser()
        
        data = {
            'target_id': str(self.kb.id),
            'target_type': 'knowledge',
            'content': '测试评论'
        }
        
        serializer = CommentCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        # 验证失败
        self.assertFalse(serializer.is_valid())

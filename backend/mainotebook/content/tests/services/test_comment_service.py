"""评论服务单元测试

测试评论服务的各项功能，包括：
- 创建评论（验证内容长度、禁言状态）
- 回复评论（验证父评论有效性）
- 删除评论（权限验证、级联删除子评论）
- 点赞评论（增加点赞数、防重复点赞）
- 取消点赞评论（减少点赞数）
- 获取评论树形结构

验证需求：4.1, 4.2, 4.4, 4.5, 4.6, 4.11, 4.12, 4.13
"""

from django.test import TestCase
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from datetime import timedelta
from mainotebook.system.models import Users
from ..models import Comment, CommentReaction, KnowledgeBase
from ..services.comment_service import CommentService


class CommentServiceTest(TestCase):
    """评论服务单元测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建测试用户
        self.user1 = Users.objects.create(
            username="testuser1",
            name="测试用户1",
            email="test1@example.com"
        )
        self.user2 = Users.objects.create(
            username="testuser2",
            name="测试用户2",
            email="test2@example.com"
        )
        self.admin_user = Users.objects.create(
            username="admin",
            name="管理员",
            email="admin@example.com",
            is_staff=True
        )
        
        # 创建测试知识库作为评论目标
        self.knowledge_base = KnowledgeBase.objects.create(
            name="测试知识库",
            description="用于测试评论",
            uploader=self.user1
        )
    
    def tearDown(self):
        """测试后清理"""
        # 清理测试数据
        CommentReaction.objects.all().delete()
        Comment.objects.all().delete()
        KnowledgeBase.objects.all().delete()
        Users.objects.all().delete()
    
    # ========== 创建评论测试 ==========
    
    def test_create_comment_with_valid_data(self):
        """测试使用有效数据创建评论（需求 4.1）"""
        data = {
            'target_id': str(self.knowledge_base.id),
            'target_type': 'knowledge',
            'content': '这是一条测试评论'
        }
        
        comment = CommentService.create_comment(self.user1, data)
        
        # 验证评论创建成功
        self.assertIsNotNone(comment)
        self.assertEqual(comment.user, self.user1)
        self.assertEqual(comment.target_id, str(self.knowledge_base.id))
        self.assertEqual(comment.target_type, 'knowledge')
        self.assertEqual(comment.content, '这是一条测试评论')
        self.assertIsNone(comment.parent_id)
        self.assertFalse(comment.is_deleted)
        self.assertEqual(comment.like_count, 0)
        self.assertEqual(comment.dislike_count, 0)
    
    def test_create_comment_by_muted_user(self):
        """测试被禁言用户创建评论应该失败（需求 4.13）"""
        # 设置用户为禁言状态（未来时间）
        self.user1.is_muted = True
        self.user1.muted_until = timezone.now() + timedelta(days=1)
        self.user1.save()
        
        data = {
            'target_id': str(self.knowledge_base.id),
            'target_type': 'knowledge',
            'content': '禁言用户的评论'
        }
        
        # 尝试创建评论
        with self.assertRaises(ValidationError) as context:
            CommentService.create_comment(self.user1, data)
        
        self.assertIn("禁言", str(context.exception))
    
    def test_create_comment_by_user_with_expired_mute(self):
        """测试禁言已过期的用户可以创建评论（需求 4.13）"""
        # 设置用户为禁言状态（过去时间）
        self.user1.is_muted = True
        self.user1.muted_until = timezone.now() - timedelta(days=1)
        self.user1.save()
        
        data = {
            'target_id': str(self.knowledge_base.id),
            'target_type': 'knowledge',
            'content': '禁言已过期的评论'
        }
        
        # 创建评论应该成功
        comment = CommentService.create_comment(self.user1, data)
        
        self.assertIsNotNone(comment)
        self.assertEqual(comment.content, '禁言已过期的评论')
    
    def test_create_comment_by_permanently_muted_user(self):
        """测试永久禁言用户创建评论应该失败（需求 4.13）"""
        # 设置用户为永久禁言状态（muted_until 为 None）
        self.user1.is_muted = True
        self.user1.muted_until = None
        self.user1.save()
        
        data = {
            'target_id': str(self.knowledge_base.id),
            'target_type': 'knowledge',
            'content': '永久禁言用户的评论'
        }
        
        # 尝试创建评论
        with self.assertRaises(ValidationError) as context:
            CommentService.create_comment(self.user1, data)
        
        self.assertIn("禁言", str(context.exception))
    
    # ========== 回复评论测试 ==========
    
    def test_create_reply_to_comment(self):
        """测试回复评论（需求 4.2）"""
        # 创建父评论
        parent_comment = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='父评论'
        )
        
        # 创建回复
        data = {
            'target_id': str(self.knowledge_base.id),
            'target_type': 'knowledge',
            'content': '这是一条回复',
            'parent': parent_comment.id
        }
        
        reply = CommentService.create_comment(self.user2, data)
        
        # 验证回复创建成功
        self.assertIsNotNone(reply)
        self.assertEqual(reply.parent_id, parent_comment.id)
        self.assertEqual(reply.content, '这是一条回复')
        self.assertEqual(reply.user, self.user2)
    
    def test_create_reply_to_deleted_comment(self):
        """测试回复已删除的评论应该失败（需求 4.12）"""
        # 创建已删除的父评论
        parent_comment = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='已删除的评论',
            is_deleted=True
        )
        
        # 尝试回复
        data = {
            'target_id': str(self.knowledge_base.id),
            'target_type': 'knowledge',
            'content': '回复已删除的评论',
            'parent': parent_comment.id
        }
        
        with self.assertRaises(ValidationError) as context:
            CommentService.create_comment(self.user2, data)
        
        self.assertIn("已被删除", str(context.exception))
    
    def test_create_reply_to_nonexistent_comment(self):
        """测试回复不存在的评论应该失败（需求 4.12）"""
        # 使用不存在的评论 ID
        import uuid
        nonexistent_id = uuid.uuid4()
        
        data = {
            'target_id': str(self.knowledge_base.id),
            'target_type': 'knowledge',
            'content': '回复不存在的评论',
            'parent': nonexistent_id
        }
        
        with self.assertRaises(ValidationError) as context:
            CommentService.create_comment(self.user2, data)
        
        self.assertIn("不存在", str(context.exception))
    
    # ========== 删除评论测试 ==========
    
    def test_delete_comment_by_owner(self):
        """测试创建者删除评论应该成功（需求 4.6）"""
        # 创建评论
        comment = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='待删除的评论'
        )
        
        # 删除评论
        CommentService.delete_comment(comment, self.user1)
        
        # 验证评论被软删除
        comment.refresh_from_db()
        self.assertTrue(comment.is_deleted)
    
    def test_delete_comment_by_admin(self):
        """测试管理员删除评论应该成功（需求 4.6）"""
        # 用户1创建评论
        comment = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='用户1的评论'
        )
        
        # 管理员删除评论
        CommentService.delete_comment(comment, self.admin_user)
        
        # 验证评论被软删除
        comment.refresh_from_db()
        self.assertTrue(comment.is_deleted)
    
    def test_delete_comment_by_non_owner(self):
        """测试非创建者删除评论应该失败（需求 4.6）"""
        # 用户1创建评论
        comment = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='用户1的评论'
        )
        
        # 用户2尝试删除
        with self.assertRaises(PermissionDenied) as context:
            CommentService.delete_comment(comment, self.user2)
        
        self.assertIn("创建者", str(context.exception))
        
        # 验证评论未被删除
        comment.refresh_from_db()
        self.assertFalse(comment.is_deleted)
    
    def test_delete_comment_cascades_to_replies(self):
        """测试删除评论会级联删除所有子评论（需求 4.6）"""
        # 创建父评论
        parent = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='父评论'
        )
        
        # 创建子评论
        child1 = Comment.objects.create(
            user=self.user2,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='子评论1',
            parent=parent
        )
        
        child2 = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='子评论2',
            parent=parent
        )
        
        # 创建孙评论
        grandchild = Comment.objects.create(
            user=self.user2,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='孙评论',
            parent=child1
        )
        
        # 删除父评论
        CommentService.delete_comment(parent, self.user1)
        
        # 验证所有评论都被软删除
        parent.refresh_from_db()
        child1.refresh_from_db()
        child2.refresh_from_db()
        grandchild.refresh_from_db()
        
        self.assertTrue(parent.is_deleted)
        self.assertTrue(child1.is_deleted)
        self.assertTrue(child2.is_deleted)
        self.assertTrue(grandchild.is_deleted)
    
    # ========== 点赞评论测试 ==========
    
    def test_like_comment(self):
        """测试点赞评论（需求 4.4）"""
        # 创建评论
        comment = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='待点赞的评论'
        )
        
        # 点赞评论
        CommentService.like_comment(comment, self.user2)
        
        # 验证点赞数增加
        comment.refresh_from_db()
        self.assertEqual(comment.like_count, 1)
        
        # 验证点赞记录创建
        reaction = CommentReaction.objects.filter(
            user=self.user2,
            comment=comment,
            reaction_type='like'
        ).first()
        self.assertIsNotNone(reaction)
    
    def test_like_comment_twice(self):
        """测试重复点赞评论不会增加计数（需求 4.4）"""
        # 创建评论
        comment = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='待点赞的评论'
        )
        
        # 第一次点赞
        CommentService.like_comment(comment, self.user2)
        comment.refresh_from_db()
        self.assertEqual(comment.like_count, 1)
        
        # 第二次点赞
        CommentService.like_comment(comment, self.user2)
        comment.refresh_from_db()
        
        # 验证点赞数不变
        self.assertEqual(comment.like_count, 1)
        
        # 验证只有一条点赞记录
        reaction_count = CommentReaction.objects.filter(
            user=self.user2,
            comment=comment,
            reaction_type='like'
        ).count()
        self.assertEqual(reaction_count, 1)
    
    def test_like_comment_after_dislike(self):
        """测试点踩后点赞会转换反应类型（需求 4.4）"""
        # 创建评论
        comment = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='待点赞的评论',
            dislike_count=1
        )
        
        # 先创建点踩记录
        CommentReaction.objects.create(
            user=self.user2,
            comment=comment,
            reaction_type='dislike'
        )
        
        # 点赞评论
        CommentService.like_comment(comment, self.user2)
        
        # 验证点赞数增加，点踩数减少
        comment.refresh_from_db()
        self.assertEqual(comment.like_count, 1)
        self.assertEqual(comment.dislike_count, 0)
        
        # 验证反应记录变为点赞
        reaction = CommentReaction.objects.get(
            user=self.user2,
            comment=comment
        )
        self.assertEqual(reaction.reaction_type, 'like')
    
    def test_multiple_users_like_comment(self):
        """测试多个用户点赞评论（需求 4.4）"""
        # 创建评论
        comment = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='待点赞的评论'
        )
        
        # 多个用户点赞
        CommentService.like_comment(comment, self.user1)
        CommentService.like_comment(comment, self.user2)
        CommentService.like_comment(comment, self.admin_user)
        
        # 验证点赞数
        comment.refresh_from_db()
        self.assertEqual(comment.like_count, 3)
        
        # 验证点赞记录数
        reaction_count = CommentReaction.objects.filter(
            comment=comment,
            reaction_type='like'
        ).count()
        self.assertEqual(reaction_count, 3)
    
    # ========== 取消点赞评论测试 ==========
    
    def test_unlike_comment(self):
        """测试取消点赞评论（需求 4.5）"""
        # 创建评论
        comment = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='已点赞的评论',
            like_count=1
        )
        
        # 创建点赞记录
        CommentReaction.objects.create(
            user=self.user2,
            comment=comment,
            reaction_type='like'
        )
        
        # 取消点赞
        CommentService.unlike_comment(comment, self.user2)
        
        # 验证点赞数减少
        comment.refresh_from_db()
        self.assertEqual(comment.like_count, 0)
        
        # 验证点赞记录被删除
        reaction_exists = CommentReaction.objects.filter(
            user=self.user2,
            comment=comment,
            reaction_type='like'
        ).exists()
        self.assertFalse(reaction_exists)
    
    def test_unlike_comment_without_like(self):
        """测试取消未点赞的评论不会影响计数（需求 4.5）"""
        # 创建评论
        comment = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='未点赞的评论',
            like_count=0
        )
        
        # 取消点赞（用户未点赞过）
        CommentService.unlike_comment(comment, self.user2)
        
        # 验证点赞数不变
        comment.refresh_from_db()
        self.assertEqual(comment.like_count, 0)
    
    def test_unlike_comment_does_not_go_negative(self):
        """测试取消点赞不会使计数变为负数（需求 4.5）"""
        # 创建评论（点赞数为0）
        comment = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='评论',
            like_count=0
        )
        
        # 创建点赞记录（模拟数据不一致的情况）
        CommentReaction.objects.create(
            user=self.user2,
            comment=comment,
            reaction_type='like'
        )
        
        # 取消点赞
        CommentService.unlike_comment(comment, self.user2)
        
        # 验证点赞数不会变为负数
        comment.refresh_from_db()
        self.assertEqual(comment.like_count, 0)
    
    # ========== 获取评论树形结构测试 ==========
    
    def test_get_comments_tree_empty(self):
        """测试获取空评论列表（需求 4.3）"""
        # 获取评论树
        comments = CommentService.get_comments_tree(
            str(self.knowledge_base.id),
            'knowledge'
        )
        
        # 验证结果为空
        self.assertEqual(len(comments), 0)
    
    def test_get_comments_tree_single_level(self):
        """测试获取单层评论列表（需求 4.3）"""
        # 创建多条评论
        comment1 = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='评论1'
        )
        comment2 = Comment.objects.create(
            user=self.user2,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='评论2'
        )
        
        # 获取评论树
        comments = CommentService.get_comments_tree(
            str(self.knowledge_base.id),
            'knowledge'
        )
        
        # 验证结果
        self.assertEqual(len(comments), 2)
        comment_ids = [c.id for c in comments]
        self.assertIn(comment1.id, comment_ids)
        self.assertIn(comment2.id, comment_ids)
        
        # 验证每条评论都有 _prefetched_replies 属性
        for comment in comments:
            self.assertTrue(hasattr(comment, '_prefetched_replies'))
            self.assertEqual(len(comment._prefetched_replies), 0)
    
    def test_get_comments_tree_with_replies(self):
        """测试获取包含回复的评论树（需求 4.3, 4.9）"""
        # 创建父评论
        parent = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='父评论'
        )
        
        # 创建子评论
        child1 = Comment.objects.create(
            user=self.user2,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='子评论1',
            parent=parent
        )
        
        child2 = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='子评论2',
            parent=parent
        )
        
        # 获取评论树
        comments = CommentService.get_comments_tree(
            str(self.knowledge_base.id),
            'knowledge'
        )
        
        # 验证结果
        self.assertEqual(len(comments), 1)  # 只有一个根评论
        root_comment = comments[0]
        self.assertEqual(root_comment.id, parent.id)
        
        # 验证子评论
        self.assertTrue(hasattr(root_comment, '_prefetched_replies'))
        self.assertEqual(len(root_comment._prefetched_replies), 2)
        
        reply_ids = [r.id for r in root_comment._prefetched_replies]
        self.assertIn(child1.id, reply_ids)
        self.assertIn(child2.id, reply_ids)
    
    def test_get_comments_tree_multi_level(self):
        """测试获取多层嵌套的评论树（需求 4.3, 4.9）"""
        # 创建父评论
        parent = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='父评论'
        )
        
        # 创建子评论
        child = Comment.objects.create(
            user=self.user2,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='子评论',
            parent=parent
        )
        
        # 创建孙评论
        grandchild = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='孙评论',
            parent=child
        )
        
        # 获取评论树
        comments = CommentService.get_comments_tree(
            str(self.knowledge_base.id),
            'knowledge'
        )
        
        # 验证结构
        self.assertEqual(len(comments), 1)
        root = comments[0]
        self.assertEqual(root.id, parent.id)
        self.assertEqual(len(root._prefetched_replies), 1)
        
        child_comment = root._prefetched_replies[0]
        self.assertEqual(child_comment.id, child.id)
        self.assertEqual(len(child_comment._prefetched_replies), 1)
        
        grandchild_comment = child_comment._prefetched_replies[0]
        self.assertEqual(grandchild_comment.id, grandchild.id)
        self.assertEqual(len(grandchild_comment._prefetched_replies), 0)
    
    def test_get_comments_tree_excludes_deleted(self):
        """测试获取评论树不包含已删除的评论（需求 4.3）"""
        # 创建正常评论
        comment1 = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='正常评论'
        )
        
        # 创建已删除的评论
        Comment.objects.create(
            user=self.user2,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='已删除的评论',
            is_deleted=True
        )
        
        # 获取评论树
        comments = CommentService.get_comments_tree(
            str(self.knowledge_base.id),
            'knowledge'
        )
        
        # 验证结果只包含未删除的评论
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].id, comment1.id)
    
    def test_get_comments_tree_ordering(self):
        """测试评论树按创建时间排序（需求 4.3）"""
        # 创建多条评论（按时间顺序）
        comment1 = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='最早的评论'
        )
        
        comment2 = Comment.objects.create(
            user=self.user2,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='中间的评论'
        )
        
        comment3 = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='最新的评论'
        )
        
        # 获取评论树
        comments = CommentService.get_comments_tree(
            str(self.knowledge_base.id),
            'knowledge'
        )
        
        # 验证排序（按创建时间正序）
        self.assertEqual(len(comments), 3)
        self.assertEqual(comments[0].id, comment1.id)
        self.assertEqual(comments[1].id, comment2.id)
        self.assertEqual(comments[2].id, comment3.id)
    
    def test_get_comments_tree_filters_by_target(self):
        """测试评论树按目标过滤（需求 4.3）"""
        # 创建另一个知识库
        kb2 = KnowledgeBase.objects.create(
            name="另一个知识库",
            description="描述",
            uploader=self.user2
        )
        
        # 为第一个知识库创建评论
        comment1 = Comment.objects.create(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge',
            content='知识库1的评论'
        )
        
        # 为第二个知识库创建评论
        Comment.objects.create(
            user=self.user2,
            target_id=str(kb2.id),
            target_type='knowledge',
            content='知识库2的评论'
        )
        
        # 获取第一个知识库的评论树
        comments = CommentService.get_comments_tree(
            str(self.knowledge_base.id),
            'knowledge'
        )
        
        # 验证结果只包含第一个知识库的评论
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].id, comment1.id)

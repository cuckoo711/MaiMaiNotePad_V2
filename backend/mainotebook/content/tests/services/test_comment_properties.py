"""评论属性测试模块

使用 Hypothesis 进行基于属性的测试，验证评论系统的核心属性。

**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.13**
"""

import uuid
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from hypothesis import given, settings, strategies as st, assume
from hypothesis.extra.django import TestCase

from mainotebook.system.models import Users
from mainotebook.content.models import Comment, CommentReaction, KnowledgeBase, PersonaCard
from mainotebook.content.services.comment_service import CommentService


# 配置 Hypothesis
settings.register_profile("default", max_examples=100, deadline=None)
settings.load_profile("default")


# 自定义策略：生成有效的评论内容（1-500 字符）
valid_comment_content = st.text(
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'P', 'Z'),
    ),
    min_size=1,
    max_size=500
).filter(lambda x: x.strip() != '')

# 自定义策略：生成无效的评论内容（超过 500 字符或空白）
invalid_comment_content = st.one_of(
    # 超过 500 字符
    st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
        min_size=501,
        max_size=1000
    ),
    # 空白字符
    st.just(''),
    st.just('   '),
    st.just('\n\n'),
    st.just('\t\t')
)

# 自定义策略：生成目标类型
target_type_strategy = st.sampled_from(['knowledge', 'persona'])



class CommentContentLengthPropertyTest(TestCase):
    """评论内容长度限制属性测试
    
    **属性 16：评论内容长度限制**
    **Validates: Requirements 4.1**
    
    验证评论内容的长度限制：
    - 长度不超过 500 字符且不为空的评论应创建成功
    - 长度超过 500 字符的评论应创建失败
    - 空白字符的评论应创建失败
    """
    
    @given(
        content=valid_comment_content,
        target_type=target_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_16_valid_content_length_succeeds(self, content, target_type):
        """属性 16：有效长度的评论内容应创建成功
        
        **Validates: Requirements 4.1**
        
        对于任意长度不超过 500 字符且不为空的评论内容，
        创建评论应该成功。
        """
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password',
            name=f'User {uuid.uuid4().hex[:4]}'
        )
        
        # 创建目标对象
        if target_type == 'knowledge':
            target = KnowledgeBase.objects.create(
                name=f'KB {uuid.uuid4().hex[:8]}',
                description='Test knowledge base',
                uploader=user
            )
        else:
            target = PersonaCard.objects.create(
                name=f'PC {uuid.uuid4().hex[:8]}',
                description='Test persona card',
                uploader=user
            )
        
        # 创建评论
        comment = CommentService.create_comment(user, {
            'target_id': str(target.id),
            'target_type': target_type,
            'content': content,
            'parent': None
        })
        
        # 断言：评论应创建成功
        self.assertIsNotNone(comment, "评论应创建成功")
        self.assertEqual(comment.content, content, "评论内容应与输入一致")
        self.assertEqual(comment.user, user, "评论用户应与创建用户一致")
        self.assertEqual(comment.target_id, str(target.id), "目标 ID 应正确")
        self.assertEqual(comment.target_type, target_type, "目标类型应正确")
        self.assertLessEqual(len(comment.content), 500, "评论内容长度应不超过 500 字符")

    
    @given(
        content=invalid_comment_content,
        target_type=target_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_16_invalid_content_length_fails(self, content, target_type):
        """属性 16：无效长度的评论内容应创建失败
        
        **Validates: Requirements 4.1**
        
        对于任意长度超过 500 字符或为空白字符的评论内容，
        创建评论应该失败。
        """
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password',
            name=f'User {uuid.uuid4().hex[:4]}'
        )
        
        # 创建目标对象
        if target_type == 'knowledge':
            target = KnowledgeBase.objects.create(
                name=f'KB {uuid.uuid4().hex[:8]}',
                description='Test knowledge base',
                uploader=user
            )
        else:
            target = PersonaCard.objects.create(
                name=f'PC {uuid.uuid4().hex[:8]}',
                description='Test persona card',
                uploader=user
            )
        
        # 断言：创建评论应失败
        with self.assertRaises(ValidationError, msg="无效长度的评论内容应创建失败"):
            CommentService.create_comment(user, {
                'target_id': str(target.id),
                'target_type': target_type,
                'content': content,
                'parent': None
            })



class CommentReplyParentPropertyTest(TestCase):
    """评论回复关联父评论属性测试
    
    **属性 17：回复关联父评论**
    **Validates: Requirements 4.2**
    
    验证回复评论的父评论关联：
    - 回复评论的 parent 字段应指向存在且未被删除的评论
    - 父评论不存在时回复应失败
    - 父评论已被删除时回复应失败
    """
    
    @given(
        parent_content=valid_comment_content,
        reply_content=valid_comment_content,
        target_type=target_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_17_reply_links_to_valid_parent(self, parent_content, reply_content, target_type):
        """属性 17：回复应关联有效的父评论
        
        **Validates: Requirements 4.2**
        
        对于任意回复评论，其 parent 字段应该指向一个存在且未被删除的评论。
        """
        # 跳过相同内容的情况
        assume(parent_content != reply_content)
        
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password',
            name=f'User {uuid.uuid4().hex[:4]}'
        )
        
        # 创建目标对象
        if target_type == 'knowledge':
            target = KnowledgeBase.objects.create(
                name=f'KB {uuid.uuid4().hex[:8]}',
                description='Test knowledge base',
                uploader=user
            )
        else:
            target = PersonaCard.objects.create(
                name=f'PC {uuid.uuid4().hex[:8]}',
                description='Test persona card',
                uploader=user
            )
        
        # 创建父评论
        parent_comment = CommentService.create_comment(user, {
            'target_id': str(target.id),
            'target_type': target_type,
            'content': parent_content,
            'parent': None
        })
        
        # 创建回复评论
        reply_comment = CommentService.create_comment(user, {
            'target_id': str(target.id),
            'target_type': target_type,
            'content': reply_content,
            'parent': parent_comment.id
        })
        
        # 断言：回复评论应关联父评论
        self.assertIsNotNone(reply_comment, "回复评论应创建成功")
        self.assertEqual(reply_comment.parent_id, parent_comment.id, "回复的 parent 应指向父评论")
        
        # 验证父评论存在且未被删除
        parent_from_db = Comment.objects.get(id=parent_comment.id)
        self.assertIsNotNone(parent_from_db, "父评论应存在")
        self.assertFalse(parent_from_db.is_deleted, "父评论不应被删除")

    
    @given(
        content=valid_comment_content,
        target_type=target_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_17_reply_to_deleted_parent_fails(self, content, target_type):
        """属性 17：回复已删除的父评论应失败
        
        **Validates: Requirements 4.2**
        
        对于任意已被删除的父评论，尝试回复应该失败。
        """
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password',
            name=f'User {uuid.uuid4().hex[:4]}'
        )
        
        # 创建目标对象
        if target_type == 'knowledge':
            target = KnowledgeBase.objects.create(
                name=f'KB {uuid.uuid4().hex[:8]}',
                description='Test knowledge base',
                uploader=user
            )
        else:
            target = PersonaCard.objects.create(
                name=f'PC {uuid.uuid4().hex[:8]}',
                description='Test persona card',
                uploader=user
            )
        
        # 创建父评论
        parent_comment = CommentService.create_comment(user, {
            'target_id': str(target.id),
            'target_type': target_type,
            'content': 'Parent comment',
            'parent': None
        })
        
        # 删除父评论
        CommentService.delete_comment(parent_comment, user)
        
        # 断言：回复已删除的父评论应失败
        with self.assertRaises(ValidationError, msg="回复已删除的父评论应失败"):
            CommentService.create_comment(user, {
                'target_id': str(target.id),
                'target_type': target_type,
                'content': content,
                'parent': parent_comment.id
            })
    
    @given(
        content=valid_comment_content,
        target_type=target_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_17_reply_to_nonexistent_parent_fails(self, content, target_type):
        """属性 17：回复不存在的父评论应失败
        
        **Validates: Requirements 4.2**
        
        对于任意不存在的父评论 ID，尝试回复应该失败。
        """
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password',
            name=f'User {uuid.uuid4().hex[:4]}'
        )
        
        # 创建目标对象
        if target_type == 'knowledge':
            target = KnowledgeBase.objects.create(
                name=f'KB {uuid.uuid4().hex[:8]}',
                description='Test knowledge base',
                uploader=user
            )
        else:
            target = PersonaCard.objects.create(
                name=f'PC {uuid.uuid4().hex[:8]}',
                description='Test persona card',
                uploader=user
            )
        
        # 生成不存在的父评论 ID
        nonexistent_parent_id = uuid.uuid4()
        
        # 断言：回复不存在的父评论应失败
        with self.assertRaises(ValidationError, msg="回复不存在的父评论应失败"):
            CommentService.create_comment(user, {
                'target_id': str(target.id),
                'target_type': target_type,
                'content': content,
                'parent': nonexistent_parent_id
            })



class CommentListTargetPropertyTest(TestCase):
    """评论列表属于指定目标属性测试
    
    **属性 18：评论列表属于指定目标**
    **Validates: Requirements 4.3**
    
    验证评论列表查询的正确性：
    - 查询结果中的所有评论应属于指定的目标
    - target_id 和 target_type 应与查询参数一致
    - 不应包含其他目标的评论
    """
    
    @given(
        content1=valid_comment_content,
        content2=valid_comment_content,
        target_type=target_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_18_comment_list_belongs_to_target(self, content1, content2, target_type):
        """属性 18：评论列表属于指定目标
        
        **Validates: Requirements 4.3**
        
        对于任意目标的评论列表查询，
        返回的所有评论的 target_id 和 target_type 都应该与查询参数一致。
        """
        # 跳过相同内容的情况
        assume(content1 != content2)
        
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password',
            name=f'User {uuid.uuid4().hex[:4]}'
        )
        
        # 创建两个目标对象
        if target_type == 'knowledge':
            target1 = KnowledgeBase.objects.create(
                name=f'KB1 {uuid.uuid4().hex[:8]}',
                description='Test knowledge base 1',
                uploader=user
            )
            target2 = KnowledgeBase.objects.create(
                name=f'KB2 {uuid.uuid4().hex[:8]}',
                description='Test knowledge base 2',
                uploader=user
            )
        else:
            target1 = PersonaCard.objects.create(
                name=f'PC1 {uuid.uuid4().hex[:8]}',
                description='Test persona card 1',
                uploader=user
            )
            target2 = PersonaCard.objects.create(
                name=f'PC2 {uuid.uuid4().hex[:8]}',
                description='Test persona card 2',
                uploader=user
            )
        
        # 为目标1创建评论
        comment1 = CommentService.create_comment(user, {
            'target_id': str(target1.id),
            'target_type': target_type,
            'content': content1,
            'parent': None
        })
        
        # 为目标2创建评论
        comment2 = CommentService.create_comment(user, {
            'target_id': str(target2.id),
            'target_type': target_type,
            'content': content2,
            'parent': None
        })
        
        # 获取目标1的评论列表
        comments_target1 = CommentService.get_comments_tree(str(target1.id), target_type)
        
        # 断言：评论列表不应为空
        self.assertGreater(len(comments_target1), 0, "目标1应有评论")
        
        # 断言：所有评论都应属于目标1
        for comment in comments_target1:
            self.assertEqual(
                comment.target_id,
                str(target1.id),
                f"评论的 target_id 应为目标1的 ID"
            )
            self.assertEqual(
                comment.target_type,
                target_type,
                f"评论的 target_type 应为 {target_type}"
            )
        
        # 断言：目标1的评论列表应包含 comment1
        comment1_ids = [str(c.id) for c in comments_target1]
        self.assertIn(str(comment1.id), comment1_ids, "目标1的评论列表应包含 comment1")
        
        # 断言：目标1的评论列表不应包含 comment2
        self.assertNotIn(str(comment2.id), comment1_ids, "目标1的评论列表不应包含 comment2")



class CommentLikeRoundTripPropertyTest(TestCase):
    """评论点赞往返保持计数属性测试
    
    **属性 19：点赞往返保持计数**
    **Validates: Requirements 4.4, 4.5**
    
    验证评论点赞和取消点赞的计数正确性：
    - 点赞后 like_count 应增加 1
    - 取消点赞后 like_count 应恢复到原始值
    - 点赞往返操作应保持计数一致性
    """
    
    @given(
        content=valid_comment_content,
        target_type=target_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_19_like_roundtrip_preserves_count(self, content, target_type):
        """属性 19：点赞往返保持计数
        
        **Validates: Requirements 4.4, 4.5**
        
        对于任意评论，点赞后 like_count 增加 1，
        取消点赞后 like_count 应该恢复到原始值。
        """
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password',
            name=f'User {uuid.uuid4().hex[:4]}'
        )
        
        # 创建目标对象
        if target_type == 'knowledge':
            target = KnowledgeBase.objects.create(
                name=f'KB {uuid.uuid4().hex[:8]}',
                description='Test knowledge base',
                uploader=user
            )
        else:
            target = PersonaCard.objects.create(
                name=f'PC {uuid.uuid4().hex[:8]}',
                description='Test persona card',
                uploader=user
            )
        
        # 创建评论
        comment = CommentService.create_comment(user, {
            'target_id': str(target.id),
            'target_type': target_type,
            'content': content,
            'parent': None
        })
        
        # 记录原始点赞数
        original_like_count = comment.like_count
        self.assertEqual(original_like_count, 0, "新评论的点赞数应为 0")
        
        # 点赞评论
        CommentService.like_comment(comment, user)
        comment.refresh_from_db()
        
        # 断言：点赞后 like_count 应增加 1
        self.assertEqual(
            comment.like_count,
            original_like_count + 1,
            "点赞后 like_count 应增加 1"
        )
        
        # 验证点赞记录存在
        reaction_exists = CommentReaction.objects.filter(
            user=user,
            comment=comment,
            reaction_type='like'
        ).exists()
        self.assertTrue(reaction_exists, "点赞记录应存在")
        
        # 取消点赞
        CommentService.unlike_comment(comment, user)
        comment.refresh_from_db()
        
        # 断言：取消点赞后 like_count 应恢复到原始值
        self.assertEqual(
            comment.like_count,
            original_like_count,
            "取消点赞后 like_count 应恢复到原始值"
        )
        
        # 验证点赞记录已删除
        reaction_exists_after = CommentReaction.objects.filter(
            user=user,
            comment=comment,
            reaction_type='like'
        ).exists()
        self.assertFalse(reaction_exists_after, "点赞记录应被删除")
    
    @given(
        content=valid_comment_content,
        target_type=target_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_19_multiple_users_like_count(self, content, target_type):
        """属性 19：多用户点赞计数正确
        
        **Validates: Requirements 4.4, 4.5**
        
        对于任意评论，多个用户点赞后 like_count 应正确累加，
        部分用户取消点赞后计数应正确减少。
        """
        # 创建多个用户
        user1 = Users.objects.create(
            username=f'user1_{uuid.uuid4().hex[:8]}',
            password='test_password',
            name=f'User1 {uuid.uuid4().hex[:4]}'
        )
        user2 = Users.objects.create(
            username=f'user2_{uuid.uuid4().hex[:8]}',
            password='test_password',
            name=f'User2 {uuid.uuid4().hex[:4]}'
        )
        user3 = Users.objects.create(
            username=f'user3_{uuid.uuid4().hex[:8]}',
            password='test_password',
            name=f'User3 {uuid.uuid4().hex[:4]}'
        )
        
        # 创建目标对象
        if target_type == 'knowledge':
            target = KnowledgeBase.objects.create(
                name=f'KB {uuid.uuid4().hex[:8]}',
                description='Test knowledge base',
                uploader=user1
            )
        else:
            target = PersonaCard.objects.create(
                name=f'PC {uuid.uuid4().hex[:8]}',
                description='Test persona card',
                uploader=user1
            )
        
        # 创建评论
        comment = CommentService.create_comment(user1, {
            'target_id': str(target.id),
            'target_type': target_type,
            'content': content,
            'parent': None
        })
        
        # 记录原始点赞数
        original_like_count = comment.like_count
        
        # 三个用户依次点赞
        CommentService.like_comment(comment, user1)
        comment.refresh_from_db()
        self.assertEqual(comment.like_count, original_like_count + 1, "第一个用户点赞后计数应为 1")
        
        CommentService.like_comment(comment, user2)
        comment.refresh_from_db()
        self.assertEqual(comment.like_count, original_like_count + 2, "第二个用户点赞后计数应为 2")
        
        CommentService.like_comment(comment, user3)
        comment.refresh_from_db()
        self.assertEqual(comment.like_count, original_like_count + 3, "第三个用户点赞后计数应为 3")
        
        # 用户2取消点赞
        CommentService.unlike_comment(comment, user2)
        comment.refresh_from_db()
        self.assertEqual(comment.like_count, original_like_count + 2, "用户2取消点赞后计数应为 2")
        
        # 用户1取消点赞
        CommentService.unlike_comment(comment, user1)
        comment.refresh_from_db()
        self.assertEqual(comment.like_count, original_like_count + 1, "用户1取消点赞后计数应为 1")
        
        # 用户3取消点赞
        CommentService.unlike_comment(comment, user3)
        comment.refresh_from_db()
        self.assertEqual(comment.like_count, original_like_count, "所有用户取消点赞后计数应恢复到原始值")



class CommentDeleteCascadePropertyTest(TestCase):
    """评论删除级联删除回复属性测试
    
    **属性 20：删除评论级联删除回复**
    **Validates: Requirements 4.6**
    
    验证评论删除的级联效果：
    - 删除评论后该评论的 is_deleted 应为 True
    - 删除评论后所有子评论（递归）的 is_deleted 应为 True
    - 级联删除应递归处理多级回复
    """
    
    @given(
        parent_content=valid_comment_content,
        reply_content=valid_comment_content,
        target_type=target_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_20_delete_cascades_to_replies(self, parent_content, reply_content, target_type):
        """属性 20：删除评论级联删除回复
        
        **Validates: Requirements 4.6**
        
        对于任意评论，删除后该评论及其所有子评论（递归）的 is_deleted 都应该为 True。
        """
        # 跳过相同内容的情况
        assume(parent_content != reply_content)
        
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password',
            name=f'User {uuid.uuid4().hex[:4]}'
        )
        
        # 创建目标对象
        if target_type == 'knowledge':
            target = KnowledgeBase.objects.create(
                name=f'KB {uuid.uuid4().hex[:8]}',
                description='Test knowledge base',
                uploader=user
            )
        else:
            target = PersonaCard.objects.create(
                name=f'PC {uuid.uuid4().hex[:8]}',
                description='Test persona card',
                uploader=user
            )
        
        # 创建父评论
        parent_comment = CommentService.create_comment(user, {
            'target_id': str(target.id),
            'target_type': target_type,
            'content': parent_content,
            'parent': None
        })
        
        # 创建子评论
        child_comment = CommentService.create_comment(user, {
            'target_id': str(target.id),
            'target_type': target_type,
            'content': reply_content,
            'parent': parent_comment.id
        })
        
        # 验证初始状态
        self.assertFalse(parent_comment.is_deleted, "父评论初始状态不应被删除")
        self.assertFalse(child_comment.is_deleted, "子评论初始状态不应被删除")
        
        # 删除父评论
        CommentService.delete_comment(parent_comment, user)
        
        # 刷新数据
        parent_comment.refresh_from_db()
        child_comment.refresh_from_db()
        
        # 断言：父评论应被标记为已删除
        self.assertTrue(parent_comment.is_deleted, "删除后父评论的 is_deleted 应为 True")
        
        # 断言：子评论应被级联删除
        self.assertTrue(child_comment.is_deleted, "删除父评论后子评论的 is_deleted 应为 True")
    
    @given(
        content1=valid_comment_content,
        content2=valid_comment_content,
        content3=valid_comment_content,
        target_type=target_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_20_delete_cascades_recursively(self, content1, content2, content3, target_type):
        """属性 20：删除评论递归级联删除多级回复
        
        **Validates: Requirements 4.6**
        
        对于任意多级嵌套的评论，删除根评论后所有层级的子评论都应该被删除。
        """
        # 跳过相同内容的情况
        assume(content1 != content2 and content2 != content3 and content1 != content3)
        
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password',
            name=f'User {uuid.uuid4().hex[:4]}'
        )
        
        # 创建目标对象
        if target_type == 'knowledge':
            target = KnowledgeBase.objects.create(
                name=f'KB {uuid.uuid4().hex[:8]}',
                description='Test knowledge base',
                uploader=user
            )
        else:
            target = PersonaCard.objects.create(
                name=f'PC {uuid.uuid4().hex[:8]}',
                description='Test persona card',
                uploader=user
            )
        
        # 创建三级嵌套评论
        # 第一级：根评论
        level1_comment = CommentService.create_comment(user, {
            'target_id': str(target.id),
            'target_type': target_type,
            'content': content1,
            'parent': None
        })
        
        # 第二级：回复根评论
        level2_comment = CommentService.create_comment(user, {
            'target_id': str(target.id),
            'target_type': target_type,
            'content': content2,
            'parent': level1_comment.id
        })
        
        # 第三级：回复第二级评论
        level3_comment = CommentService.create_comment(user, {
            'target_id': str(target.id),
            'target_type': target_type,
            'content': content3,
            'parent': level2_comment.id
        })
        
        # 验证初始状态
        self.assertFalse(level1_comment.is_deleted, "第一级评论初始状态不应被删除")
        self.assertFalse(level2_comment.is_deleted, "第二级评论初始状态不应被删除")
        self.assertFalse(level3_comment.is_deleted, "第三级评论初始状态不应被删除")
        
        # 删除根评论
        CommentService.delete_comment(level1_comment, user)
        
        # 刷新数据
        level1_comment.refresh_from_db()
        level2_comment.refresh_from_db()
        level3_comment.refresh_from_db()
        
        # 断言：所有层级的评论都应被标记为已删除
        self.assertTrue(level1_comment.is_deleted, "第一级评论应被删除")
        self.assertTrue(level2_comment.is_deleted, "第二级评论应被级联删除")
        self.assertTrue(level3_comment.is_deleted, "第三级评论应被递归级联删除")



class MutedUserCannotCommentPropertyTest(TestCase):
    """禁言用户无法评论属性测试
    
    **属性 26：禁言用户无法评论**
    **Validates: Requirements 4.13**
    
    验证禁言用户的评论限制：
    - 被禁言的用户（is_muted=True 且 muted_until 未过期）无法发表评论
    - 被禁言的用户无法发表回复
    - 禁言期已过的用户可以正常评论
    - 未被禁言的用户可以正常评论
    """
    
    @given(
        content=valid_comment_content,
        target_type=target_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_26_muted_user_cannot_comment(self, content, target_type):
        """属性 26：禁言用户无法评论
        
        **Validates: Requirements 4.13**
        
        对于任意被禁言的用户（is_muted=True 且 muted_until 未过期），
        其发表评论或回复的操作应该被拒绝。
        """
        # 创建被禁言的用户
        muted_user = Users.objects.create(
            username=f'muted_user_{uuid.uuid4().hex[:8]}',
            password='test_password',
            name=f'Muted User {uuid.uuid4().hex[:4]}',
            is_muted=True,
            muted_until=timezone.now() + timedelta(days=7)  # 禁言7天
        )
        
        # 创建目标对象
        if target_type == 'knowledge':
            target = KnowledgeBase.objects.create(
                name=f'KB {uuid.uuid4().hex[:8]}',
                description='Test knowledge base',
                uploader=muted_user
            )
        else:
            target = PersonaCard.objects.create(
                name=f'PC {uuid.uuid4().hex[:8]}',
                description='Test persona card',
                uploader=muted_user
            )
        
        # 断言：禁言用户发表评论应失败
        with self.assertRaises(ValidationError, msg="禁言用户不应能发表评论"):
            CommentService.create_comment(muted_user, {
                'target_id': str(target.id),
                'target_type': target_type,
                'content': content,
                'parent': None
            })
    
    @given(
        content=valid_comment_content,
        reply_content=valid_comment_content,
        target_type=target_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_26_muted_user_cannot_reply(self, content, reply_content, target_type):
        """属性 26：禁言用户无法回复
        
        **Validates: Requirements 4.13**
        
        对于任意被禁言的用户，其回复评论的操作应该被拒绝。
        """
        # 跳过相同内容的情况
        assume(content != reply_content)
        
        # 创建正常用户
        normal_user = Users.objects.create(
            username=f'normal_user_{uuid.uuid4().hex[:8]}',
            password='test_password',
            name=f'Normal User {uuid.uuid4().hex[:4]}'
        )
        
        # 创建被禁言的用户
        muted_user = Users.objects.create(
            username=f'muted_user_{uuid.uuid4().hex[:8]}',
            password='test_password',
            name=f'Muted User {uuid.uuid4().hex[:4]}',
            is_muted=True,
            muted_until=timezone.now() + timedelta(days=7)
        )
        
        # 创建目标对象
        if target_type == 'knowledge':
            target = KnowledgeBase.objects.create(
                name=f'KB {uuid.uuid4().hex[:8]}',
                description='Test knowledge base',
                uploader=normal_user
            )
        else:
            target = PersonaCard.objects.create(
                name=f'PC {uuid.uuid4().hex[:8]}',
                description='Test persona card',
                uploader=normal_user
            )
        
        # 正常用户创建评论
        parent_comment = CommentService.create_comment(normal_user, {
            'target_id': str(target.id),
            'target_type': target_type,
            'content': content,
            'parent': None
        })
        
        # 断言：禁言用户回复评论应失败
        with self.assertRaises(ValidationError, msg="禁言用户不应能回复评论"):
            CommentService.create_comment(muted_user, {
                'target_id': str(target.id),
                'target_type': target_type,
                'content': reply_content,
                'parent': parent_comment.id
            })
    
    @given(
        content=valid_comment_content,
        target_type=target_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_26_expired_mute_allows_comment(self, content, target_type):
        """属性 26：禁言期已过的用户可以评论
        
        **Validates: Requirements 4.13**
        
        对于禁言期已过的用户（muted_until 已过期），
        应该可以正常发表评论。
        """
        # 创建禁言期已过的用户
        expired_mute_user = Users.objects.create(
            username=f'expired_mute_user_{uuid.uuid4().hex[:8]}',
            password='test_password',
            name=f'Expired Mute User {uuid.uuid4().hex[:4]}',
            is_muted=True,
            muted_until=timezone.now() - timedelta(days=1)  # 禁言期已过
        )
        
        # 创建目标对象
        if target_type == 'knowledge':
            target = KnowledgeBase.objects.create(
                name=f'KB {uuid.uuid4().hex[:8]}',
                description='Test knowledge base',
                uploader=expired_mute_user
            )
        else:
            target = PersonaCard.objects.create(
                name=f'PC {uuid.uuid4().hex[:8]}',
                description='Test persona card',
                uploader=expired_mute_user
            )
        
        # 断言：禁言期已过的用户应能发表评论
        comment = CommentService.create_comment(expired_mute_user, {
            'target_id': str(target.id),
            'target_type': target_type,
            'content': content,
            'parent': None
        })
        
        self.assertIsNotNone(comment, "禁言期已过的用户应能发表评论")
        self.assertEqual(comment.user, expired_mute_user, "评论用户应正确")
        self.assertEqual(comment.content, content, "评论内容应正确")
    
    @given(
        content=valid_comment_content,
        target_type=target_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_26_unmuted_user_can_comment(self, content, target_type):
        """属性 26：未被禁言的用户可以评论
        
        **Validates: Requirements 4.13**
        
        对于未被禁言的用户（is_muted=False），
        应该可以正常发表评论。
        """
        # 创建未被禁言的用户
        normal_user = Users.objects.create(
            username=f'normal_user_{uuid.uuid4().hex[:8]}',
            password='test_password',
            name=f'Normal User {uuid.uuid4().hex[:4]}',
            is_muted=False
        )
        
        # 创建目标对象
        if target_type == 'knowledge':
            target = KnowledgeBase.objects.create(
                name=f'KB {uuid.uuid4().hex[:8]}',
                description='Test knowledge base',
                uploader=normal_user
            )
        else:
            target = PersonaCard.objects.create(
                name=f'PC {uuid.uuid4().hex[:8]}',
                description='Test persona card',
                uploader=normal_user
            )
        
        # 断言：未被禁言的用户应能发表评论
        comment = CommentService.create_comment(normal_user, {
            'target_id': str(target.id),
            'target_type': target_type,
            'content': content,
            'parent': None
        })
        
        self.assertIsNotNone(comment, "未被禁言的用户应能发表评论")
        self.assertEqual(comment.user, normal_user, "评论用户应正确")
        self.assertEqual(comment.content, content, "评论内容应正确")
    
    @given(
        content=valid_comment_content,
        target_type=target_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_26_permanent_mute_blocks_comment(self, content, target_type):
        """属性 26：永久禁言用户无法评论
        
        **Validates: Requirements 4.13**
        
        对于永久禁言的用户（is_muted=True 且 muted_until=None），
        其发表评论的操作应该被拒绝。
        """
        # 创建永久禁言的用户
        permanent_mute_user = Users.objects.create(
            username=f'permanent_mute_user_{uuid.uuid4().hex[:8]}',
            password='test_password',
            name=f'Permanent Mute User {uuid.uuid4().hex[:4]}',
            is_muted=True,
            muted_until=None  # 永久禁言
        )
        
        # 创建目标对象
        if target_type == 'knowledge':
            target = KnowledgeBase.objects.create(
                name=f'KB {uuid.uuid4().hex[:8]}',
                description='Test knowledge base',
                uploader=permanent_mute_user
            )
        else:
            target = PersonaCard.objects.create(
                name=f'PC {uuid.uuid4().hex[:8]}',
                description='Test persona card',
                uploader=permanent_mute_user
            )
        
        # 断言：永久禁言用户发表评论应失败
        with self.assertRaises(ValidationError, msg="永久禁言用户不应能发表评论"):
            CommentService.create_comment(permanent_mute_user, {
                'target_id': str(target.id),
                'target_type': target_type,
                'content': content,
                'parent': None
            })

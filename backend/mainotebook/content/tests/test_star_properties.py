"""收藏属性测试模块

使用 Hypothesis 进行基于属性的测试，验证收藏系统的核心属性。

**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.7, 5.10**
"""

import uuid
from django.core.exceptions import ValidationError
from hypothesis import given, settings, strategies as st, assume
from hypothesis.extra.django import TestCase

from mainotebook.system.models import Users
from mainotebook.content.models import StarRecord, KnowledgeBase, PersonaCard
from mainotebook.content.services.star_service import StarService


# 配置 Hypothesis
settings.register_profile("default", max_examples=100, deadline=None)
settings.load_profile("default")


# 自定义策略：生成目标类型
target_type_strategy = st.sampled_from(['knowledge', 'persona'])


class StarRoundTripPropertyTest(TestCase):
    """收藏往返保持计数属性测试
    
    **属性 21：收藏往返保持计数**
    **Validates: Requirements 5.1, 5.2, 5.3, 5.4**
    
    验证收藏和取消收藏的计数正确性：
    - 收藏后 star_count 应增加 1
    - 取消收藏后 star_count 应恢复到原始值
    - 收藏往返操作应保持计数一致性
    """
    
    @given(target_type=target_type_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_21_star_roundtrip_preserves_count(self, target_type):
        """属性 21：收藏往返保持计数
        
        **Validates: Requirements 5.1, 5.2, 5.3, 5.4**
        
        对于任意知识库或人设卡，收藏后 star_count 增加 1，
        取消收藏后 star_count 应该恢复到原始值。
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
        
        # 记录原始收藏数
        original_star_count = target.star_count
        self.assertEqual(original_star_count, 0, "新内容的收藏数应为 0")
        
        # 收藏内容
        StarService.star_content(user, str(target.id), target_type)
        target.refresh_from_db()
        
        # 断言：收藏后 star_count 应增加 1
        self.assertEqual(
            target.star_count,
            original_star_count + 1,
            "收藏后 star_count 应增加 1"
        )
        
        # 验证收藏记录存在
        star_exists = StarRecord.objects.filter(
            user=user,
            target_id=str(target.id),
            target_type=target_type
        ).exists()
        self.assertTrue(star_exists, "收藏记录应存在")
        
        # 取消收藏
        StarService.unstar_content(user, str(target.id), target_type)
        target.refresh_from_db()
        
        # 断言：取消收藏后 star_count 应恢复到原始值
        self.assertEqual(
            target.star_count,
            original_star_count,
            "取消收藏后 star_count 应恢复到原始值"
        )
        
        # 验证收藏记录已删除
        star_exists_after = StarRecord.objects.filter(
            user=user,
            target_id=str(target.id),
            target_type=target_type
        ).exists()
        self.assertFalse(star_exists_after, "收藏记录应被删除")
    
    @given(target_type=target_type_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_21_multiple_users_star_count(self, target_type):
        """属性 21：多用户收藏计数正确
        
        **Validates: Requirements 5.1, 5.2, 5.3, 5.4**
        
        对于任意内容，多个用户收藏后 star_count 应正确累加，
        部分用户取消收藏后计数应正确减少。
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
        
        # 记录原始收藏数
        original_star_count = target.star_count
        
        # 三个用户依次收藏
        StarService.star_content(user1, str(target.id), target_type)
        target.refresh_from_db()
        self.assertEqual(target.star_count, original_star_count + 1, "第一个用户收藏后计数应为 1")
        
        StarService.star_content(user2, str(target.id), target_type)
        target.refresh_from_db()
        self.assertEqual(target.star_count, original_star_count + 2, "第二个用户收藏后计数应为 2")
        
        StarService.star_content(user3, str(target.id), target_type)
        target.refresh_from_db()
        self.assertEqual(target.star_count, original_star_count + 3, "第三个用户收藏后计数应为 3")
        
        # 用户2取消收藏
        StarService.unstar_content(user2, str(target.id), target_type)
        target.refresh_from_db()
        self.assertEqual(target.star_count, original_star_count + 2, "用户2取消收藏后计数应为 2")
        
        # 用户1取消收藏
        StarService.unstar_content(user1, str(target.id), target_type)
        target.refresh_from_db()
        self.assertEqual(target.star_count, original_star_count + 1, "用户1取消收藏后计数应为 1")
        
        # 用户3取消收藏
        StarService.unstar_content(user3, str(target.id), target_type)
        target.refresh_from_db()
        self.assertEqual(target.star_count, original_star_count, "所有用户取消收藏后计数应恢复到原始值")


class StarListBelongsToUserPropertyTest(TestCase):
    """收藏列表属于用户属性测试
    
    **属性 22：收藏列表属于用户**
    **Validates: Requirements 5.5**
    
    验证收藏列表查询的正确性：
    - 查询结果中的所有收藏记录应属于指定用户
    - user 字段应与查询参数一致
    - 不应包含其他用户的收藏记录
    """
    
    @given(target_type=target_type_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_22_star_list_belongs_to_user(self, target_type):
        """属性 22：收藏列表属于用户
        
        **Validates: Requirements 5.5**
        
        对于任意用户的收藏列表查询，
        返回的所有收藏记录的 user 都应该是该用户。
        """
        # 创建两个用户
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
        
        # 创建两个目标对象
        if target_type == 'knowledge':
            target1 = KnowledgeBase.objects.create(
                name=f'KB1 {uuid.uuid4().hex[:8]}',
                description='Test knowledge base 1',
                uploader=user1
            )
            target2 = KnowledgeBase.objects.create(
                name=f'KB2 {uuid.uuid4().hex[:8]}',
                description='Test knowledge base 2',
                uploader=user1
            )
        else:
            target1 = PersonaCard.objects.create(
                name=f'PC1 {uuid.uuid4().hex[:8]}',
                description='Test persona card 1',
                uploader=user1
            )
            target2 = PersonaCard.objects.create(
                name=f'PC2 {uuid.uuid4().hex[:8]}',
                description='Test persona card 2',
                uploader=user1
            )
        
        # 用户1收藏目标1
        StarService.star_content(user1, str(target1.id), target_type)
        
        # 用户2收藏目标2
        StarService.star_content(user2, str(target2.id), target_type)
        
        # 获取用户1的收藏列表
        user1_stars = StarService.get_user_stars(user1, target_type)
        
        # 断言：收藏列表不应为空
        self.assertGreater(user1_stars.count(), 0, "用户1应有收藏")
        
        # 断言：所有收藏记录都应属于用户1
        for star in user1_stars:
            self.assertEqual(
                star.user_id,
                user1.id,
                f"收藏记录的 user 应为用户1"
            )
        
        # 断言：用户1的收藏列表应包含目标1
        target1_ids = [star.target_id for star in user1_stars]
        self.assertIn(str(target1.id), target1_ids, "用户1的收藏列表应包含目标1")
        
        # 断言：用户1的收藏列表不应包含目标2
        self.assertNotIn(str(target2.id), target1_ids, "用户1的收藏列表不应包含目标2")
    
    @given(target_type=target_type_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_22_star_list_filtered_by_type(self, target_type):
        """属性 22：收藏列表按类型筛选正确
        
        **Validates: Requirements 5.5**
        
        对于任意用户的收藏列表查询，
        按类型筛选后返回的所有收藏记录的 target_type 都应该与筛选条件一致。
        """
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password',
            name=f'User {uuid.uuid4().hex[:4]}'
        )
        
        # 创建知识库和人设卡
        knowledge_base = KnowledgeBase.objects.create(
            name=f'KB {uuid.uuid4().hex[:8]}',
            description='Test knowledge base',
            uploader=user
        )
        persona_card = PersonaCard.objects.create(
            name=f'PC {uuid.uuid4().hex[:8]}',
            description='Test persona card',
            uploader=user
        )
        
        # 用户收藏知识库和人设卡
        StarService.star_content(user, str(knowledge_base.id), 'knowledge')
        StarService.star_content(user, str(persona_card.id), 'persona')
        
        # 获取用户的指定类型收藏列表
        filtered_stars = StarService.get_user_stars(user, target_type)
        
        # 断言：收藏列表不应为空
        self.assertGreater(filtered_stars.count(), 0, f"用户应有 {target_type} 类型的收藏")
        
        # 断言：所有收藏记录的 target_type 都应与筛选条件一致
        for star in filtered_stars:
            self.assertEqual(
                star.target_type,
                target_type,
                f"收藏记录的 target_type 应为 {target_type}"
            )


class PreventDuplicateStarPropertyTest(TestCase):
    """防止重复收藏属性测试
    
    **属性 23：防止重复收藏**
    **Validates: Requirements 5.7, 5.10**
    
    验证防止重复收藏的机制：
    - 第一次收藏应该成功
    - 第二次收藏同一内容应该失败
    - 取消收藏后可以再次收藏
    """
    
    @given(target_type=target_type_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_23_prevent_duplicate_star(self, target_type):
        """属性 23：防止重复收藏
        
        **Validates: Requirements 5.7, 5.10**
        
        对于任意用户和内容，第一次收藏应该成功，
        第二次收藏同一内容应该失败。
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
        
        # 第一次收藏应该成功
        StarService.star_content(user, str(target.id), target_type)
        
        # 验证收藏记录存在
        star_count = StarRecord.objects.filter(
            user=user,
            target_id=str(target.id),
            target_type=target_type
        ).count()
        self.assertEqual(star_count, 1, "第一次收藏应创建一条记录")
        
        # 第二次收藏同一内容应该失败
        with self.assertRaises(ValidationError, msg="重复收藏应该失败"):
            StarService.star_content(user, str(target.id), target_type)
        
        # 验证收藏记录仍然只有一条
        star_count_after = StarRecord.objects.filter(
            user=user,
            target_id=str(target.id),
            target_type=target_type
        ).count()
        self.assertEqual(star_count_after, 1, "重复收藏不应创建新记录")
    
    @given(target_type=target_type_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_23_can_restar_after_unstar(self, target_type):
        """属性 23：取消收藏后可以再次收藏
        
        **Validates: Requirements 5.7, 5.10**
        
        对于任意用户和内容，取消收藏后应该可以再次收藏。
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
        
        # 第一次收藏
        StarService.star_content(user, str(target.id), target_type)
        
        # 取消收藏
        StarService.unstar_content(user, str(target.id), target_type)
        
        # 验证收藏记录已删除
        star_exists = StarRecord.objects.filter(
            user=user,
            target_id=str(target.id),
            target_type=target_type
        ).exists()
        self.assertFalse(star_exists, "取消收藏后记录应被删除")
        
        # 再次收藏应该成功
        StarService.star_content(user, str(target.id), target_type)
        
        # 验证收藏记录重新创建
        star_exists_after = StarRecord.objects.filter(
            user=user,
            target_id=str(target.id),
            target_type=target_type
        ).exists()
        self.assertTrue(star_exists_after, "再次收藏应创建新记录")
        
        # 验证收藏计数正确
        target.refresh_from_db()
        self.assertEqual(target.star_count, 1, "再次收藏后计数应为 1")
    
    @given(target_type=target_type_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_23_different_users_can_star_same_content(self, target_type):
        """属性 23：不同用户可以收藏同一内容
        
        **Validates: Requirements 5.7, 5.10**
        
        对于任意内容，不同用户应该都可以收藏，
        防重复收藏机制只针对同一用户。
        """
        # 创建两个用户
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
        
        # 用户1收藏
        StarService.star_content(user1, str(target.id), target_type)
        
        # 用户2收藏同一内容应该成功
        StarService.star_content(user2, str(target.id), target_type)
        
        # 验证两条收藏记录都存在
        user1_star_exists = StarRecord.objects.filter(
            user=user1,
            target_id=str(target.id),
            target_type=target_type
        ).exists()
        user2_star_exists = StarRecord.objects.filter(
            user=user2,
            target_id=str(target.id),
            target_type=target_type
        ).exists()
        
        self.assertTrue(user1_star_exists, "用户1的收藏记录应存在")
        self.assertTrue(user2_star_exists, "用户2的收藏记录应存在")
        
        # 验证收藏计数正确
        target.refresh_from_db()
        self.assertEqual(target.star_count, 2, "两个用户收藏后计数应为 2")

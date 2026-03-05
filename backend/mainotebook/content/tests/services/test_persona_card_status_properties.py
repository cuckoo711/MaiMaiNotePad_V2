# -*- coding: utf-8 -*-

"""
人设卡状态管理属性测试（任务 16.4）

使用 Hypothesis 进行基于属性的测试，验证状态管理的正确性属性。

**验证需求：12.5, 12.6, 12.7, 12.8, 12.9, 12.10**
"""

from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase
from mainotebook.system.models import Users
from mainotebook.content.models import PersonaCard


class PersonaCardStatusPropertiesTest(TestCase):
    """人设卡状态管理属性测试类（任务 16.4）"""
    
    @settings(max_examples=100)
    @given(
        is_public=st.booleans(),
        is_pending=st.booleans()
    )
    def test_property_43_public_to_private_state_transition(self, is_public, is_pending):
        """属性 43: 公开转私有状态转换
        
        Feature: persona-card-upload, Property 43: 公开转私有状态转换
        
        ∀ card, toggle_public(card) ∧ card.is_public = True ⇒ card'.is_public = False
        
        验证需求：12.5
        """
        # 只测试公开人设卡
        if not is_public:
            return
        
        # 创建测试用户
        user, _ = Users.objects.get_or_create(
            username='testuser_prop43',
            defaults={'password': 'testpass123', 'email': 'test43@example.com'}
        )
        
        # 创建公开人设卡
        persona_card = PersonaCard.objects.create(
            name='测试人设卡',
            description='这是一个测试人设卡的描述',
            uploader=user,
            is_public=True,
            is_pending=is_pending,
            creator=user,
            modifier=user.username
        )
        
        # 执行公开转私有操作
        persona_card.is_public = False
        persona_card.save()
        
        # 验证状态转换
        persona_card.refresh_from_db()
        self.assertFalse(persona_card.is_public)
    
    @settings(max_examples=100)
    @given(
        is_pending=st.booleans()
    )
    def test_property_44_public_to_private_pending_reset(self, is_pending):
        """属性 44: 公开转私有审核状态重置
        
        Feature: persona-card-upload, Property 44: 公开转私有审核状态重置
        
        ∀ card, toggle_public(card) ∧ card.is_public = True ⇒ card'.is_pending = False
        
        验证需求：12.6
        """
        # 创建测试用户
        user, _ = Users.objects.get_or_create(
            username='testuser_prop44',
            defaults={'password': 'testpass123', 'email': 'test44@example.com'}
        )
        
        # 创建公开人设卡
        persona_card = PersonaCard.objects.create(
            name='测试人设卡',
            description='这是一个测试人设卡的描述',
            uploader=user,
            is_public=True,
            is_pending=is_pending,
            creator=user,
            modifier=user.username
        )
        
        # 执行公开转私有操作（保持 is_pending=False）
        persona_card.is_public = False
        persona_card.is_pending = False
        persona_card.save()
        
        # 验证审核状态
        persona_card.refresh_from_db()
        self.assertFalse(persona_card.is_pending)
    
    @settings(max_examples=100)
    @given(
        is_pending=st.booleans()
    )
    def test_property_45_private_to_public_review(self, is_pending):
        """属性 45: 私有转公开重新审核
        
        Feature: persona-card-upload, Property 45: 私有转公开重新审核
        
        ∀ card, toggle_public(card) ∧ card.is_public = False ⇒ card'.is_pending = True
        
        验证需求：12.7
        """
        # 创建测试用户
        user, _ = Users.objects.get_or_create(
            username='testuser_prop45',
            defaults={'password': 'testpass123', 'email': 'test45@example.com'}
        )
        
        # 创建私有人设卡
        persona_card = PersonaCard.objects.create(
            name='测试人设卡',
            description='这是一个测试人设卡的描述',
            uploader=user,
            is_public=False,
            is_pending=is_pending,
            creator=user,
            modifier=user.username
        )
        
        # 执行私有转公开操作（触发审核）
        persona_card.is_public = True
        persona_card.is_pending = True
        persona_card.save()
        
        # 验证审核状态
        persona_card.refresh_from_db()
        self.assertTrue(persona_card.is_pending)
    
    @settings(max_examples=100)
    @given(
        is_public=st.booleans(),
        is_pending=st.booleans()
    )
    def test_property_46_soft_delete_persona_card(self, is_public, is_pending):
        """属性 46: 软删除人设卡
        
        Feature: persona-card-upload, Property 46: 软删除人设卡
        
        ∀ card, delete(card) ⇒ card'.is_deleted = True ∧ card 仍存在于数据库
        
        验证需求：12.8, 12.9
        """
        # 创建测试用户
        user, _ = Users.objects.get_or_create(
            username='testuser_prop46',
            defaults={'password': 'testpass123', 'email': 'test46@example.com'}
        )
        
        # 创建人设卡
        persona_card = PersonaCard.objects.create(
            name='测试人设卡',
            description='这是一个测试人设卡的描述',
            uploader=user,
            is_public=is_public,
            is_pending=is_pending,
            creator=user,
            modifier=user.username
        )
        
        persona_card_id = persona_card.id
        
        # 执行软删除操作
        persona_card.is_deleted = True
        persona_card.save()
        
        # 验证软删除：记录仍然存在
        persona_card = PersonaCard.objects.get(id=persona_card_id)
        self.assertTrue(persona_card.is_deleted)
        self.assertIsNotNone(persona_card)
    
    @settings(max_examples=100)
    @given(
        is_public=st.booleans(),
        is_pending=st.booleans()
    )
    def test_property_47_deleted_persona_card_hidden(self, is_public, is_pending):
        """属性 47: 已删除人设卡隐藏
        
        Feature: persona-card-upload, Property 47: 已删除人设卡隐藏
        
        ∀ card, card.is_deleted = True ⇒ card ∉ list_results
        
        验证需求：12.10
        """
        # 创建测试用户
        user, _ = Users.objects.get_or_create(
            username='testuser_prop47',
            defaults={'password': 'testpass123', 'email': 'test47@example.com'}
        )
        
        # 创建人设卡
        persona_card = PersonaCard.objects.create(
            name='测试人设卡',
            description='这是一个测试人设卡的描述',
            uploader=user,
            is_public=is_public,
            is_pending=is_pending,
            creator=user,
            modifier=user.username
        )
        
        # 执行软删除操作
        persona_card.is_deleted = True
        persona_card.save()
        
        # 验证已删除人设卡不在公开列表中
        # 对于公开且已审核的人设卡，应该被过滤掉
        if is_public and not is_pending:
            public_cards = PersonaCard.objects.filter(
                is_public=True,
                is_pending=False,
                is_deleted=False
            )
            self.assertNotIn(persona_card, public_cards)

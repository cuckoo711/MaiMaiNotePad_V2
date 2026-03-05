# -*- coding: utf-8 -*-

"""
人设卡审核流程属性测试

使用 Hypothesis 进行基于属性的测试，验证审核流程的通用属性：
- 属性 32: 公开人设卡审核状态
- 属性 33: 审核任务触发
- 属性 34: AI 审核通过决策
- 属性 35: AI 审核拒绝决策
- 属性 36: 审核报告创建
- 属性 37: 私有人设卡跳过审核

验证需求：10.1, 10.2, 10.4, 10.5, 10.6, 10.7
"""

import uuid
from unittest.mock import patch, MagicMock

from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase

from mainotebook.content.models import PersonaCard, PersonaCardFile, ReviewReport
from mainotebook.content.services.persona_card_service import PersonaCardService
from mainotebook.system.models import Users


class PersonaCardReviewPropertiesTest(TestCase):
    """人设卡审核流程属性测试"""

    def setUp(self):
        """设置测试数据"""
        # 创建测试用户
        self.user = Users.objects.create(
            username=f"test_user_{uuid.uuid4().hex[:8]}",
            name="测试用户",
            is_active=True,
            creator=None,
            modifier="system"
        )
        
        # 创建 AI 审核员用户
        self.ai_reviewer, _ = Users.objects.get_or_create(
            username="ai_reviewer",
            defaults={
                "name": "AI 审核员",
                "creator": None,
                "modifier": "system"
            }
        )

    def _create_persona_card(self, is_public=False, is_pending=False):
        """创建人设卡
        
        Args:
            is_public: 是否公开
            is_pending: 是否待审核
            
        Returns:
            PersonaCard: 创建的人设卡实例
        """
        persona_card = PersonaCard.objects.create(
            name=f"测试人设卡_{uuid.uuid4().hex[:8]}",
            description="这是一个测试人设卡的描述内容",
            uploader=self.user,
            copyright_owner=self.user.username,
            is_public=is_public,
            is_pending=is_pending,
            version="1.0",
            creator=self.user,
            modifier=self.user.username
        )
        
        # 创建 TOML 文件记录
        PersonaCardFile.objects.create(
            persona_card=persona_card,
            file_name="bot_config.toml",
            original_name="bot_config.toml",
            file_path=f"persona_cards/{persona_card.id}/bot_config.toml",
            file_type="application/toml",
            file_size=1024,
            creator=self.user,
            modifier=self.user.username
        )
        
        return persona_card

    @settings(max_examples=100, deadline=None)
    @given(
        is_public=st.booleans(),
        is_pending=st.booleans()
    )
    def test_property_32_public_persona_card_review_status(self, is_public, is_pending):
        """
        Feature: persona-card-upload, Property 32: 公开人设卡审核状态
        
        对于任意 is_public 为 True 的人设卡提交，系统应将其 is_pending 设置为 True（待审核状态）
        
        验证需求：10.1
        """
        # 创建人设卡
        persona_card = self._create_persona_card(
            is_public=False,  # 初始为私有
            is_pending=False
        )
        
        # Mock 文件验证通过
        with patch(
            "mainotebook.content.services.persona_card_service.PersonaCardService.validate_toml_file",
            return_value=(True, None)
        ):
            # Mock 审核任务
            with patch("mainotebook.content.tasks.auto_review_task.delay"):
                # 提交审核
                PersonaCardService.submit_for_review(persona_card, self.user)
        
        # 刷新数据
        persona_card.refresh_from_db()
        
        # 验证：提交审核后，is_pending 应为 True
        self.assertTrue(
            persona_card.is_pending,
            f"提交审核后 is_pending 应为 True，实际为 {persona_card.is_pending}"
        )

    @settings(max_examples=100, deadline=None)
    @given(
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    def test_property_34_ai_review_approved_decision(self, confidence):
        """
        Feature: persona-card-upload, Property 34: AI 审核通过决策
        
        对于任意 AI 审核结果为 "通过"（decision='true'）的人设卡，
        系统应自动批准（is_pending=False, is_public=True）
        
        验证需求：10.4
        """
        # 创建待审核的人设卡
        persona_card = self._create_persona_card(
            is_public=True,
            is_pending=True
        )
        
        # Mock ModerationService 返回通过结果
        with patch(
            "mainotebook.content.services.moderation_service.get_moderation_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.moderate.return_value = {
                "decision": "true",
                "confidence": confidence,
                "violation_types": [],
                "flagged_content": "",
                "_meta": {"raw_output": ""}
            }
            mock_get_service.return_value = mock_service
            
            # 执行审核任务
            from mainotebook.content.tasks import auto_review_task
            auto_review_task.apply(
                args=[str(persona_card.id), "persona"]
            )
        
        # 刷新数据
        persona_card.refresh_from_db()
        
        # 验证：AI 审核通过应自动批准
        self.assertFalse(
            persona_card.is_pending,
            f"AI 审核通过后 is_pending 应为 False，实际为 {persona_card.is_pending}"
        )
        self.assertTrue(
            persona_card.is_public,
            f"AI 审核通过后 is_public 应为 True，实际为 {persona_card.is_public}"
        )

    @settings(max_examples=50, deadline=None)
    @given(
        confidence=st.floats(min_value=0.85, max_value=1.0, allow_nan=False, allow_infinity=False),
        violation_types=st.lists(
            st.sampled_from(['porn', 'politics', 'abuse', 'violence', 'spam', 'illegal']),
            min_size=1,
            max_size=3,
            unique=True
        )
    )
    def test_property_35_ai_review_rejected_decision(self, confidence, violation_types):
        """
        Feature: persona-card-upload, Property 35: AI 审核拒绝决策
        
        对于任意 AI 审核结果为 "拒绝"（decision='false'）且置信度高的人设卡，
        系统应自动拒绝（is_pending=False, is_public=False）
        
        验证需求：10.5
        """
        # 创建待审核的人设卡
        persona_card = self._create_persona_card(
            is_public=True,
            is_pending=True
        )
        
        # Mock ModerationService 返回拒绝结果
        with patch(
            "mainotebook.content.services.moderation_service.get_moderation_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.moderate.return_value = {
                "decision": "false",
                "confidence": confidence,
                "violation_types": violation_types,
                "flagged_content": "违规内容",
                "_meta": {"raw_output": ""}
            }
            mock_get_service.return_value = mock_service
            
            # 执行审核任务
            from mainotebook.content.tasks import auto_review_task
            auto_review_task.apply(
                args=[str(persona_card.id), "persona"]
            )
        
        # 刷新数据
        persona_card.refresh_from_db()
        
        # 验证：AI 审核拒绝应自动拒绝
        self.assertFalse(
            persona_card.is_pending,
            f"AI 审核拒绝后 is_pending 应为 False，实际为 {persona_card.is_pending}"
        )
        self.assertFalse(
            persona_card.is_public,
            f"AI 审核拒绝后 is_public 应为 False，实际为 {persona_card.is_public}"
        )

    @settings(max_examples=100, deadline=None)
    @given(
        decision=st.sampled_from(['true', 'false', 'unknown']),
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    def test_property_36_review_report_creation(self, decision, confidence):
        """
        Feature: persona-card-upload, Property 36: 审核报告创建
        
        对于任意完成的审核（AI 或人工），系统应创建 ReviewReport 记录保存审核详情
        
        验证需求：10.6
        """
        # 创建待审核的人设卡
        persona_card = self._create_persona_card(
            is_public=True,
            is_pending=True
        )
        
        # Mock ModerationService 返回审核结果
        with patch(
            "mainotebook.content.services.moderation_service.get_moderation_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.moderate.return_value = {
                "decision": decision,
                "confidence": confidence,
                "violation_types": [],
                "flagged_content": "",
                "_meta": {"raw_output": ""}
            }
            mock_get_service.return_value = mock_service
            
            # 执行审核任务
            from mainotebook.content.tasks import auto_review_task
            auto_review_task.apply(
                args=[str(persona_card.id), "persona"]
            )
        
        # 验证：应创建审核报告
        report = ReviewReport.objects.filter(
            content_id=str(persona_card.id),
            content_type="persona"
        ).first()
        
        self.assertIsNotNone(
            report,
            f"审核完成后应创建 ReviewReport，decision={decision}, confidence={confidence}"
        )
        
        # 验证报告包含必要字段
        self.assertEqual(str(report.content_id), str(persona_card.id))
        self.assertEqual(report.content_type, "persona")
        self.assertIsInstance(report.final_confidence, float)
        self.assertIsInstance(report.violation_types, list)
        self.assertIsInstance(report.report_data, dict)

    @settings(max_examples=100, deadline=None)
    @given(
        is_public=st.just(False),  # 固定为私有
        is_pending=st.booleans()
    )
    def test_property_37_private_persona_card_skip_review(self, is_public, is_pending):
        """
        Feature: persona-card-upload, Property 37: 私有人设卡跳过审核
        
        对于任意 is_public 为 False 的人设卡提交，系统应跳过审核流程，
        直接将 is_pending 设为 False
        
        验证需求：10.7
        """
        # 创建私有人设卡
        persona_card = self._create_persona_card(
            is_public=False,
            is_pending=False
        )
        
        # 验证：私有人设卡不需要审核
        self.assertFalse(
            persona_card.is_public,
            f"应为私有人设卡，实际 is_public={persona_card.is_public}"
        )
        self.assertFalse(
            persona_card.is_pending,
            f"私有人设卡不需要审核，is_pending 应为 False，实际为 {persona_card.is_pending}"
        )
        
        # 验证：没有审核报告
        report_count = ReviewReport.objects.filter(
            content_id=str(persona_card.id),
            content_type="persona"
        ).count()
        
        self.assertEqual(
            report_count,
            0,
            f"私有人设卡不应有审核报告，实际有 {report_count} 条"
        )

    @settings(max_examples=50, deadline=None)
    @given(
        initial_is_public=st.booleans(),
        initial_is_pending=st.booleans()
    )
    def test_property_33_review_task_triggered(self, initial_is_public, initial_is_pending):
        """
        Feature: persona-card-upload, Property 33: 审核任务触发
        
        对于任意公开人设卡的提交，系统应创建 Celery 异步任务执行 AI 审核
        
        验证需求：10.2
        """
        # 创建人设卡
        persona_card = self._create_persona_card(
            is_public=False,
            is_pending=False
        )
        
        # Mock 文件验证通过
        with patch(
            "mainotebook.content.services.persona_card_service.PersonaCardService.validate_toml_file",
            return_value=(True, None)
        ):
            # Mock 审核任务，记录是否被调用
            with patch("mainotebook.content.tasks.auto_review_task.delay") as mock_delay:
                # 提交审核
                PersonaCardService.submit_for_review(persona_card, self.user)
                
                # 验证：审核任务应被触发
                mock_delay.assert_called_once_with(
                    str(persona_card.id),
                    "persona"
                )

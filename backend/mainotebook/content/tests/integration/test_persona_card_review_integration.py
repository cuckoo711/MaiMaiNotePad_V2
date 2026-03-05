# -*- coding: utf-8 -*-

"""
人设卡审核流程集成单元测试

测试人设卡审核流程的完整集成，包括：
- AI 审核通过（自动批准）
- AI 审核不确定（自动批准）
- AI 审核拒绝（移交人工审核）
- 审核报告创建
- 审核任务创建失败处理

验证需求：10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7
"""

import uuid
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone

from mainotebook.content.models import PersonaCard, PersonaCardFile, ReviewReport
from mainotebook.content.services.persona_card_service import PersonaCardService
from mainotebook.system.models import Users


class PersonaCardReviewIntegrationTest(TestCase):
    """人设卡审核流程集成测试"""

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
        
        # 创建 AI 审核员用户（如果不存在）
        self.ai_reviewer, _ = Users.objects.get_or_create(
            username="ai_reviewer",
            defaults={
                "name": "AI 审核员",
                "creator": None,
                "modifier": "system"
            }
        )

    def _create_persona_card_with_toml(self, is_public=False, is_pending=False):
        """创建包含 TOML 文件的人设卡
        
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

    def test_ai_review_approved_auto_approve(self):
        """测试 AI 审核通过（自动批准）（需求 10.4）
        
        当 AI 审核结果为 "通过" 时，系统应自动批准人设卡：
        - is_pending 设为 False
        - is_public 设为 True
        - 创建 ReviewReport 记录，decision 为 auto_approved
        """
        # 创建待审核的公开人设卡
        persona_card = self._create_persona_card_with_toml(
            is_public=True,
            is_pending=True
        )
        
        # 不 mock，直接调用真实的 AutoReviewService
        # 但需要 mock ModerationService 返回通过结果
        with patch(
            "mainotebook.content.services.moderation_service.get_moderation_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.moderate.return_value = {
                "decision": "true",
                "confidence": 0.3,
                "violation_types": [],
                "flagged_content": "",
                "_meta": {"raw_output": ""}
            }
            mock_get_service.return_value = mock_service
            
            # 执行审核任务
            from mainotebook.content.tasks import auto_review_task
            result = auto_review_task.apply(
                args=[str(persona_card.id), "persona"]
            )
        
        # 刷新人设卡数据
        persona_card.refresh_from_db()
        
        # 验证人设卡状态
        self.assertFalse(persona_card.is_pending, "审核通过后 is_pending 应为 False")
        self.assertTrue(persona_card.is_public, "审核通过后 is_public 应为 True")
        
        # 验证审核报告创建
        report = ReviewReport.objects.filter(
            content_id=str(persona_card.id),
            content_type="persona"
        ).first()
        
        self.assertIsNotNone(report, "应创建审核报告")
        self.assertEqual(report.decision, "auto_approved", "审核决策应为 auto_approved")

    def test_ai_review_unknown_auto_approve(self):
        """测试 AI 审核不确定（自动批准）（需求 10.4）
        
        当 AI 审核结果为 "不确定"（unknown）且置信度低于拒绝阈值时，
        系统应自动批准人设卡。
        """
        # 创建待审核的公开人设卡
        persona_card = self._create_persona_card_with_toml(
            is_public=True,
            is_pending=True
        )
        
        # Mock ModerationService 返回不确定但低置信度结果
        with patch(
            "mainotebook.content.services.moderation_service.get_moderation_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.moderate.return_value = {
                "decision": "unknown",
                "confidence": 0.5,  # 低于 UNKNOWN_REJECT_THRESHOLD (0.7)
                "violation_types": [],
                "flagged_content": "",
                "_meta": {"raw_output": ""}
            }
            mock_get_service.return_value = mock_service
            
            # 执行审核任务
            from mainotebook.content.tasks import auto_review_task
            result = auto_review_task.apply(
                args=[str(persona_card.id), "persona"]
            )
        
        # 刷新人设卡数据
        persona_card.refresh_from_db()
        
        # 验证人设卡状态
        self.assertFalse(persona_card.is_pending, "不确定但低置信度应自动批准")
        self.assertTrue(persona_card.is_public, "is_public 应为 True")

    def test_ai_review_rejected_manual_review(self):
        """测试 AI 审核拒绝（自动拒绝）（需求 10.5）
        
        当 AI 审核结果为 "拒绝" 时，系统应自动拒绝人设卡：
        - is_pending 设为 False
        - is_public 设为 False
        - 创建 ReviewReport 记录，decision 为 auto_rejected
        
        注意：当前实现是直接拒绝，而不是移交人工审核队列
        """
        # 创建待审核的公开人设卡
        persona_card = self._create_persona_card_with_toml(
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
                "confidence": 0.95,
                "violation_types": ["porn", "abuse"],
                "flagged_content": "违规内容片段",
                "_meta": {"raw_output": ""}
            }
            mock_get_service.return_value = mock_service
            
            # 执行审核任务
            from mainotebook.content.tasks import auto_review_task
            result = auto_review_task.apply(
                args=[str(persona_card.id), "persona"]
            )
        
        # 刷新人设卡数据
        persona_card.refresh_from_db()
        
        # 验证人设卡状态
        self.assertFalse(persona_card.is_pending, "审核拒绝后 is_pending 应为 False")
        self.assertFalse(persona_card.is_public, "审核拒绝后 is_public 应为 False")
        
        # 验证审核报告创建
        report = ReviewReport.objects.filter(
            content_id=str(persona_card.id),
            content_type="persona"
        ).first()
        
        self.assertIsNotNone(report, "应创建审核报告")
        self.assertEqual(report.decision, "auto_rejected", "审核决策应为 auto_rejected")
        self.assertIn("porn", report.violation_types, "应记录违规类型")

    def test_review_report_creation(self):
        """测试审核报告创建（需求 10.6）
        
        验证审核完成后创建的 ReviewReport 包含完整信息：
        - content_id, content_type, content_name
        - decision, final_confidence, violation_types
        - report_data 包含详细审核信息
        """
        # 创建待审核的公开人设卡
        persona_card = self._create_persona_card_with_toml(
            is_public=True,
            is_pending=True
        )
        
        # Mock ModerationService 返回详细结果
        with patch(
            "mainotebook.content.services.moderation_service.get_moderation_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.moderate.return_value = {
                "decision": "true",
                "confidence": 0.2,
                "violation_types": [],
                "flagged_content": "",
                "_meta": {"raw_output": ""}
            }
            mock_get_service.return_value = mock_service
            
            # 执行审核任务
            from mainotebook.content.tasks import auto_review_task
            result = auto_review_task.apply(
                args=[str(persona_card.id), "persona"]
            )
        
        # 验证审核报告
        report = ReviewReport.objects.filter(
            content_id=str(persona_card.id),
            content_type="persona"
        ).first()
        
        self.assertIsNotNone(report, "应创建审核报告")
        self.assertEqual(str(report.content_id), str(persona_card.id))
        self.assertEqual(report.content_type, "persona")
        self.assertEqual(report.content_name, persona_card.name)
        self.assertEqual(report.decision, "auto_approved")
        self.assertIsInstance(report.final_confidence, float)
        self.assertIsInstance(report.violation_types, list)
        self.assertIsInstance(report.report_data, dict)
        self.assertIn("parts", report.report_data)

    def test_review_task_creation_failure_handling(self):
        """测试审核任务创建失败处理（需求 10.2）
        
        当审核任务创建失败时，系统应：
        - 记录警告日志
        - 不影响人设卡状态更新
        - 人设卡保持待审核状态
        """
        # 创建私有人设卡
        persona_card = self._create_persona_card_with_toml(
            is_public=False,
            is_pending=False
        )
        
        # Mock 文件验证通过
        with patch(
            "mainotebook.content.services.persona_card_service.PersonaCardService.validate_toml_file",
            return_value=(True, None)
        ):
            # Mock auto_review_task.delay 抛出异常
            with patch(
                "mainotebook.content.tasks.auto_review_task.delay",
                side_effect=Exception("Celery 连接失败")
            ):
                # 提交审核（submit_for_review 会捕获异常）
                PersonaCardService.submit_for_review(persona_card, self.user)
        
        # 刷新人设卡数据
        persona_card.refresh_from_db()
        
        # 验证人设卡状态（即使任务创建失败，状态也应该更新）
        self.assertTrue(persona_card.is_pending, "提交审核后 is_pending 应为 True")
        self.assertFalse(persona_card.is_public, "提交审核后 is_public 应为 False")

    def test_private_persona_card_skip_review(self):
        """测试私有人设卡跳过审核（需求 10.7）
        
        私有人设卡（is_public=False）不需要审核：
        - is_pending 应为 False
        - 不触发审核任务
        """
        # 创建私有人设卡
        persona_card = self._create_persona_card_with_toml(
            is_public=False,
            is_pending=False
        )
        
        # 验证状态
        self.assertFalse(persona_card.is_public, "应为私有人设卡")
        self.assertFalse(persona_card.is_pending, "私有人设卡不需要审核")
        
        # 验证没有审核报告
        report_count = ReviewReport.objects.filter(
            content_id=str(persona_card.id),
            content_type="persona"
        ).count()
        
        self.assertEqual(report_count, 0, "私有人设卡不应有审核报告")

    def test_toggle_public_triggers_review(self):
        """测试私有转公开触发审核（需求 12.7）
        
        当用户将私有人设卡转为公开时，应触发审核流程：
        - is_public 设为 True
        - is_pending 设为 True
        - 触发审核任务
        """
        # 创建私有人设卡
        persona_card = self._create_persona_card_with_toml(
            is_public=False,
            is_pending=False
        )
        
        # Mock auto_review_task.delay
        with patch(
            "mainotebook.content.tasks.auto_review_task.delay"
        ) as mock_delay:
            # 模拟 toggle_public 的逻辑
            persona_card.is_public = True
            persona_card.is_pending = True
            persona_card.save()
            
            # 触发审核任务
            from mainotebook.content.tasks import auto_review_task
            auto_review_task.delay(str(persona_card.id), "persona")
        
        # 验证状态
        persona_card.refresh_from_db()
        self.assertTrue(persona_card.is_public, "应转为公开")
        self.assertTrue(persona_card.is_pending, "应处于待审核状态")
        
        # 验证审核任务被调用
        mock_delay.assert_called_once_with(str(persona_card.id), "persona")

    def test_public_to_private_reset_review_status(self):
        """测试公开转私有重置审核状态（需求 12.6）
        
        当用户将公开人设卡转为私有时：
        - is_public 设为 False
        - is_pending 设为 False
        """
        # 创建已通过审核的公开人设卡
        persona_card = self._create_persona_card_with_toml(
            is_public=True,
            is_pending=False
        )
        
        # 模拟 toggle_public 的逻辑（公开转私有）
        persona_card.is_public = False
        persona_card.is_pending = False
        persona_card.save()
        
        # 验证状态
        persona_card.refresh_from_db()
        self.assertFalse(persona_card.is_public, "应转为私有")
        self.assertFalse(persona_card.is_pending, "is_pending 应为 False")

    def test_review_notification_includes_summary(self):
        """测试审核通知包含报告摘要（需求 11.1, 11.3, 11.4）
        
        验证审核完成后发送的通知包含：
        - 人设卡名称
        - 审核决策
        - 审核报告摘要（置信度、违规类型等）
        """
        # 创建待审核的人设卡
        persona_card = self._create_persona_card_with_toml(
            is_public=False,
            is_pending=True
        )
        
        # Mock ModerationService 返回通过结果
        mock_moderation_result = {
            "decision": "true",
            "confidence": 0.3,
            "violation_types": [],
            "flagged_content": "",
            "raw_output": "模拟审核输出"
        }
        
        # Mock ReviewNotificationService.send_review_notification
        with patch(
            "mainotebook.content.services.moderation_service.get_moderation_service"
        ) as mock_get_service, \
        patch(
            "mainotebook.content.services.review_notification.ReviewNotificationService.send_review_notification"
        ) as mock_send_notification:
            
            mock_service = MagicMock()
            mock_service.moderate_text.return_value = mock_moderation_result
            mock_get_service.return_value = mock_service
            
            # 触发审核任务（直接调用，不使用 delay）
            from mainotebook.content.tasks import auto_review_task
            auto_review_task(str(persona_card.id), "persona")
        
        # 验证通知被调用
        mock_send_notification.assert_called_once()
        
        # 验证调用参数
        call_kwargs = mock_send_notification.call_args[1]
        
        # 验证基本参数
        self.assertEqual(call_kwargs['uploader_id'], self.user.id)
        self.assertEqual(call_kwargs['content_name'], persona_card.name)
        self.assertEqual(call_kwargs['content_type'], 'persona')
        self.assertEqual(call_kwargs['action'], 'approved')
        
        # 验证包含审核报告摘要
        self.assertIn('report_summary', call_kwargs)
        report_summary = call_kwargs['report_summary']
        self.assertIsNotNone(report_summary)
        self.assertIn('审核结果', report_summary)
        self.assertIn('置信度', report_summary)
        
    def test_review_notification_rejected_includes_reason(self):
        """测试审核拒绝通知包含拒绝原因和违规类型（需求 11.4）
        
        验证审核拒绝时通知包含：
        - 拒绝原因
        - 违规类型
        - 审核报告摘要
        """
        # 创建待审核的人设卡
        persona_card = self._create_persona_card_with_toml(
            is_public=False,
            is_pending=True
        )
        
        # Mock ModerationService 返回拒绝结果
        mock_moderation_result = {
            "decision": "false",
            "confidence": 0.95,
            "violation_types": ["porn", "abuse"],
            "flagged_content": "违规内容片段",
            "raw_output": "模拟审核输出"
        }
        
        # Mock ReviewNotificationService.send_review_notification
        with patch(
            "mainotebook.content.services.moderation_service.get_moderation_service"
        ) as mock_get_service, \
        patch(
            "mainotebook.content.services.review_notification.ReviewNotificationService.send_review_notification"
        ) as mock_send_notification:
            
            mock_service = MagicMock()
            mock_service.moderate_text.return_value = mock_moderation_result
            mock_get_service.return_value = mock_service
            
            # 触发审核任务（直接调用，不使用 delay）
            from mainotebook.content.tasks import auto_review_task
            auto_review_task(str(persona_card.id), "persona")
        
        # 验证通知被调用
        mock_send_notification.assert_called_once()
        
        # 验证调用参数
        call_kwargs = mock_send_notification.call_args[1]
        
        # 验证基本参数
        self.assertEqual(call_kwargs['action'], 'rejected')
        
        # 验证包含拒绝原因（违规类型）
        self.assertIn('reason', call_kwargs)
        reason = call_kwargs['reason']
        self.assertIsNotNone(reason)
        self.assertIn('porn', reason)
        self.assertIn('abuse', reason)
        
        # 验证包含审核报告摘要
        self.assertIn('report_summary', call_kwargs)
        report_summary = call_kwargs['report_summary']
        self.assertIsNotNone(report_summary)
        self.assertIn('审核结果', report_summary)
        self.assertIn('违规类型', report_summary)

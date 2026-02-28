# -*- coding: utf-8 -*-

"""
AutoReviewService 单元测试

测试 execute_auto_review 完整流程、置信度边界值决策、
空内容处理、无关联文件审核、内容不存在/不在待审核状态、
以及 API 异常时状态保持等场景。

验证需求：1.1, 1.3, 2.1, 2.2, 2.3, 6.1, 6.2
"""

import uuid
from unittest.mock import MagicMock, patch, PropertyMock

from django.test import TestCase

from mainotebook.content.services.auto_review_service import AutoReviewService


def _make_mock_content(
    name: str = "测试知识库",
    description: str = "测试描述",
    content: str = "测试内容",
    is_pending: bool = True,
    is_public: bool = False,
) -> MagicMock:
    """构造 mock 内容对象

    Args:
        name: 内容名称
        description: 内容描述
        content: 内容正文
        is_pending: 是否待审核
        is_public: 是否公开

    Returns:
        MagicMock: 模拟的内容对象
    """
    mock_content = MagicMock()
    mock_content.id = uuid.uuid4()
    mock_content.name = name
    mock_content.description = description
    mock_content.content = content
    mock_content.is_pending = is_pending
    mock_content.is_public = is_public
    mock_content.uploader = MagicMock()
    mock_content.uploader.id = 1
    # 默认无关联文件
    mock_content.files.filter.return_value = []
    return mock_content


def _make_moderation_result(
    confidence: float = 0.2,
    decision: str = "true",
    violation_types: list = None,
) -> dict:
    """构造 ModerationService.moderate() 返回值

    Args:
        confidence: 违规置信度
        decision: 审核决策
        violation_types: 违规类型列表

    Returns:
        dict: 模拟的审核结果
    """
    return {
        "decision": decision,
        "confidence": confidence,
        "violation_types": violation_types or [],
    }


# 需要 mock 的模块路径常量
_PATCH_KB = "mainotebook.content.models.KnowledgeBase"
_PATCH_PC = "mainotebook.content.models.PersonaCard"
_PATCH_GET_MOD = "mainotebook.content.services.moderation_service.get_moderation_service"
_PATCH_REVIEW_SVC = "mainotebook.content.services.review_service.ReviewService"
_PATCH_USERS = "mainotebook.system.models.Users"
_PATCH_REPORT = "mainotebook.content.models.ReviewReport"
_PATCH_NOTIFY = "mainotebook.content.services.review_notification.ReviewNotificationService"


class TestExecuteAutoReviewFullFlow(TestCase):
    """execute_auto_review 完整流程测试"""

    @patch(_PATCH_NOTIFY)
    @patch(_PATCH_REPORT)
    @patch(_PATCH_USERS)
    @patch(_PATCH_REVIEW_SVC)
    @patch(_PATCH_GET_MOD)
    @patch(_PATCH_KB)
    def test_execute_auto_review_full_flow_approved(
        self,
        mock_kb_cls,
        mock_get_mod,
        mock_review_svc,
        mock_users_cls,
        mock_report_cls,
        mock_notify_cls,
    ):
        """低置信度（0.2）应自动通过，返回包含 decision 的 report_data"""
        # 构造 mock 内容
        mock_content = _make_mock_content()
        mock_kb_cls.objects.filter.return_value.first.return_value = mock_content

        # 构造 mock ModerationService
        mock_mod_svc = MagicMock()
        mock_mod_svc.moderate.return_value = _make_moderation_result(
            confidence=0.2, decision="true", violation_types=[]
        )
        mock_get_mod.return_value = mock_mod_svc

        # 构造 mock Users
        mock_ai_user = MagicMock()
        mock_users_cls.objects.get_or_create.return_value = (mock_ai_user, True)

        # 构造 mock ReviewReport
        mock_report = MagicMock()
        mock_report.report_data = {
            "content_name": "测试知识库",
            "content_type": "knowledge",
            "decision": "auto_approved",
            "final_confidence": 0.2,
            "violation_types": [],
            "parts": [],
        }
        mock_report.decision = "auto_approved"
        mock_report.violation_types = []
        mock_report_cls.objects.create.return_value = mock_report

        # 执行
        result = AutoReviewService.execute_auto_review(
            str(mock_content.id), "knowledge"
        )

        # 验证返回 report_data
        assert result["decision"] == "auto_approved"
        assert result["final_confidence"] == 0.2

        # 验证调用了 ReviewService.approve_content
        mock_review_svc.approve_content.assert_called_once_with(
            str(mock_content.id), "knowledge", mock_ai_user
        )

    @patch(_PATCH_NOTIFY)
    @patch(_PATCH_REPORT)
    @patch(_PATCH_USERS)
    @patch(_PATCH_REVIEW_SVC)
    @patch(_PATCH_GET_MOD)
    @patch(_PATCH_KB)
    def test_execute_auto_review_full_flow_rejected(
        self,
        mock_kb_cls,
        mock_get_mod,
        mock_review_svc,
        mock_users_cls,
        mock_report_cls,
        mock_notify_cls,
    ):
        """高置信度（0.9）应自动拒绝，返回包含 decision 的 report_data"""
        mock_content = _make_mock_content()
        mock_kb_cls.objects.filter.return_value.first.return_value = mock_content

        mock_mod_svc = MagicMock()
        mock_mod_svc.moderate.return_value = _make_moderation_result(
            confidence=0.9, decision="false", violation_types=["porn"]
        )
        mock_get_mod.return_value = mock_mod_svc

        mock_ai_user = MagicMock()
        mock_users_cls.objects.get_or_create.return_value = (mock_ai_user, True)

        mock_report = MagicMock()
        mock_report.report_data = {
            "content_name": "测试知识库",
            "content_type": "knowledge",
            "decision": "auto_rejected",
            "final_confidence": 0.9,
            "violation_types": ["porn"],
            "parts": [],
        }
        mock_report.decision = "auto_rejected"
        mock_report.violation_types = ["porn"]
        mock_report_cls.objects.create.return_value = mock_report

        result = AutoReviewService.execute_auto_review(
            str(mock_content.id), "knowledge"
        )

        assert result["decision"] == "auto_rejected"
        assert result["final_confidence"] == 0.9

        # 验证调用了 ReviewService.reject_content
        mock_review_svc.reject_content.assert_called_once_with(
            str(mock_content.id), "knowledge", mock_ai_user, "porn"
        )

    @patch(_PATCH_NOTIFY)
    @patch(_PATCH_REPORT)
    @patch(_PATCH_USERS)
    @patch(_PATCH_REVIEW_SVC)
    @patch(_PATCH_GET_MOD)
    @patch(_PATCH_KB)
    def test_execute_auto_review_pending_manual(
        self,
        mock_kb_cls,
        mock_get_mod,
        mock_review_svc,
        mock_users_cls,
        mock_report_cls,
        mock_notify_cls,
    ):
        """中等置信度（0.6）应保持待人工复核"""
        mock_content = _make_mock_content()
        mock_kb_cls.objects.filter.return_value.first.return_value = mock_content

        mock_mod_svc = MagicMock()
        mock_mod_svc.moderate.return_value = _make_moderation_result(
            confidence=0.6, decision="unknown", violation_types=["politics"]
        )
        mock_get_mod.return_value = mock_mod_svc

        mock_report = MagicMock()
        mock_report.report_data = {
            "content_name": "测试知识库",
            "content_type": "knowledge",
            "decision": "pending_manual",
            "final_confidence": 0.6,
            "violation_types": ["politics"],
            "parts": [],
        }
        mock_report.decision = "pending_manual"
        mock_report_cls.objects.create.return_value = mock_report

        result = AutoReviewService.execute_auto_review(
            str(mock_content.id), "knowledge"
        )

        assert result["decision"] == "pending_manual"

        # 不应调用 approve 或 reject
        mock_review_svc.approve_content.assert_not_called()
        mock_review_svc.reject_content.assert_not_called()


class TestConfidenceBoundary(TestCase):
    """置信度边界值决策测试

    验证 _make_decision 在边界值处的行为：
    - 0.0 → auto_approved（< 0.5）
    - 0.5 → pending_manual（0.5 <= x <= 0.8）
    - 0.8 → pending_manual（0.5 <= x <= 0.8）
    - 1.0 → auto_rejected（> 0.8）
    """

    @patch(_PATCH_USERS)
    @patch(_PATCH_REVIEW_SVC)
    def test_confidence_boundary_0_0(self, mock_review_svc, mock_users_cls):
        """confidence=0.0 应返回 auto_approved"""
        mock_ai_user = MagicMock()
        mock_users_cls.objects.get_or_create.return_value = (mock_ai_user, True)

        content_id = str(uuid.uuid4())
        decision = AutoReviewService._make_decision(
            content_id, "knowledge", 0.0, []
        )
        assert decision == "auto_approved"
        mock_review_svc.approve_content.assert_called_once()

    @patch(_PATCH_USERS)
    @patch(_PATCH_REVIEW_SVC)
    def test_confidence_boundary_0_5(self, mock_review_svc, mock_users_cls):
        """confidence=0.5 应返回 pending_manual（0.5 在 [0.5, 0.8] 区间内）"""
        content_id = str(uuid.uuid4())
        decision = AutoReviewService._make_decision(
            content_id, "knowledge", 0.5, ["politics"]
        )
        assert decision == "pending_manual"
        mock_review_svc.approve_content.assert_not_called()
        mock_review_svc.reject_content.assert_not_called()

    @patch(_PATCH_USERS)
    @patch(_PATCH_REVIEW_SVC)
    def test_confidence_boundary_0_8(self, mock_review_svc, mock_users_cls):
        """confidence=0.8 应返回 pending_manual（0.8 在 [0.5, 0.8] 区间内）"""
        content_id = str(uuid.uuid4())
        decision = AutoReviewService._make_decision(
            content_id, "knowledge", 0.8, ["abuse"]
        )
        assert decision == "pending_manual"
        mock_review_svc.approve_content.assert_not_called()
        mock_review_svc.reject_content.assert_not_called()

    @patch(_PATCH_USERS)
    @patch(_PATCH_REVIEW_SVC)
    def test_confidence_boundary_1_0(self, mock_review_svc, mock_users_cls):
        """confidence=1.0 应返回 auto_rejected（> 0.8）"""
        mock_ai_user = MagicMock()
        mock_users_cls.objects.get_or_create.return_value = (mock_ai_user, True)

        content_id = str(uuid.uuid4())
        decision = AutoReviewService._make_decision(
            content_id, "knowledge", 1.0, ["porn", "abuse"]
        )
        assert decision == "auto_rejected"
        mock_review_svc.reject_content.assert_called_once()


class TestEdgeCases(TestCase):
    """边界场景测试：空内容、无文件、内容不存在、内容非待审核"""

    @patch(_PATCH_NOTIFY)
    @patch(_PATCH_REPORT)
    @patch(_PATCH_USERS)
    @patch(_PATCH_REVIEW_SVC)
    @patch(_PATCH_GET_MOD)
    @patch(_PATCH_KB)
    def test_empty_content_fields(
        self,
        mock_kb_cls,
        mock_get_mod,
        mock_review_svc,
        mock_users_cls,
        mock_report_cls,
        mock_notify_cls,
    ):
        """name/description/content 全为空时，审核仍应正常完成"""
        mock_content = _make_mock_content(name="", description="", content="")
        mock_kb_cls.objects.filter.return_value.first.return_value = mock_content

        mock_mod_svc = MagicMock()
        mock_get_mod.return_value = mock_mod_svc

        # 空文本不会调用 moderate（_build_text_fields 返回空字符串）
        mock_ai_user = MagicMock()
        mock_users_cls.objects.get_or_create.return_value = (mock_ai_user, True)

        mock_report = MagicMock()
        mock_report.report_data = {
            "content_name": "",
            "content_type": "knowledge",
            "decision": "auto_approved",
            "final_confidence": 0.0,
            "violation_types": [],
            "parts": [],
        }
        mock_report.decision = "auto_approved"
        mock_report.violation_types = []
        mock_report_cls.objects.create.return_value = mock_report

        result = AutoReviewService.execute_auto_review(
            str(mock_content.id), "knowledge"
        )

        # 空内容无审核结果，聚合后 confidence=0.0 → auto_approved
        assert "error" not in result
        assert result["decision"] == "auto_approved"

    @patch(_PATCH_NOTIFY)
    @patch(_PATCH_REPORT)
    @patch(_PATCH_USERS)
    @patch(_PATCH_REVIEW_SVC)
    @patch(_PATCH_GET_MOD)
    @patch(_PATCH_KB)
    def test_no_associated_files(
        self,
        mock_kb_cls,
        mock_get_mod,
        mock_review_svc,
        mock_users_cls,
        mock_report_cls,
        mock_notify_cls,
    ):
        """无关联文件时，仅基于文本字段完成审核"""
        mock_content = _make_mock_content()
        # files.filter 返回空列表（默认行为）
        mock_kb_cls.objects.filter.return_value.first.return_value = mock_content

        mock_mod_svc = MagicMock()
        mock_mod_svc.moderate.return_value = _make_moderation_result(
            confidence=0.3, decision="true", violation_types=[]
        )
        mock_get_mod.return_value = mock_mod_svc

        mock_ai_user = MagicMock()
        mock_users_cls.objects.get_or_create.return_value = (mock_ai_user, True)

        mock_report = MagicMock()
        mock_report.report_data = {
            "content_name": "测试知识库",
            "content_type": "knowledge",
            "decision": "auto_approved",
            "final_confidence": 0.3,
            "violation_types": [],
            "parts": [
                {
                    "part_name": "文本字段",
                    "part_type": "text_field",
                    "confidence": 0.3,
                    "violation_types": [],
                }
            ],
        }
        mock_report.decision = "auto_approved"
        mock_report.violation_types = []
        mock_report_cls.objects.create.return_value = mock_report

        result = AutoReviewService.execute_auto_review(
            str(mock_content.id), "knowledge"
        )

        assert "error" not in result
        assert result["decision"] == "auto_approved"
        # moderate 仅被调用一次（文本字段）
        assert mock_mod_svc.moderate.call_count == 1

    @patch(_PATCH_KB)
    def test_content_not_found(self, mock_kb_cls):
        """内容不存在时应返回错误字典"""
        mock_kb_cls.objects.filter.return_value.first.return_value = None

        result = AutoReviewService.execute_auto_review(
            str(uuid.uuid4()), "knowledge"
        )

        assert "error" in result
        assert result["error"] == "内容不存在"

    @patch(_PATCH_KB)
    def test_content_not_pending(self, mock_kb_cls):
        """内容不在待审核状态时应返回错误字典"""
        mock_content = _make_mock_content(is_pending=False)
        mock_kb_cls.objects.filter.return_value.first.return_value = mock_content

        result = AutoReviewService.execute_auto_review(
            str(mock_content.id), "knowledge"
        )

        assert "error" in result
        assert result["error"] == "内容不在待审核状态"

    @patch(_PATCH_GET_MOD)
    @patch(_PATCH_KB)
    def test_api_failure_preserves_state(self, mock_kb_cls, mock_get_mod):
        """ModerationService 抛出异常时，应返回错误且不改变内容状态"""
        mock_content = _make_mock_content()
        mock_kb_cls.objects.filter.return_value.first.return_value = mock_content

        # get_moderation_service 抛出异常
        mock_get_mod.side_effect = Exception("API 连接超时")

        result = AutoReviewService.execute_auto_review(
            str(mock_content.id), "knowledge"
        )

        # 应返回错误
        assert "error" in result
        assert result["error"] == "AI 审核服务暂时不可用"

        # 内容状态不应被修改
        assert mock_content.is_pending is True
        assert mock_content.is_public is False

"""
AI 内容审核服务独立单元测试

测试 ModerationService 的核心逻辑，不依赖 Django 配置。
"""

import json
import os
from unittest.mock import Mock, patch

import pytest


class TestModerationServiceStandalone:
    """ModerationService 独立单元测试"""

    @patch.dict(os.environ, {}, clear=True)
    def test_init_with_api_key(self):
        """测试使用 API Key 初始化"""
        from mainotebook.content.services.moderation_service import ModerationService
        
        service = ModerationService(api_key="test-api-key")

        assert service.api_key == "test-api-key"
        assert service.base_url == "https://api.siliconflow.cn/v1"
        assert service.model == "Qwen/Qwen2.5-7B-Instruct"
        assert service.client is not None

    def test_init_from_env_variable(self, monkeypatch):
        """测试从环境变量读取 API Key"""
        monkeypatch.setenv("SILICONFLOW_API_KEY", "env-api-key")
        
        from mainotebook.content.services.moderation_service import ModerationService
        
        service = ModerationService()

        assert service.api_key == "env-api-key"

    def test_init_without_api_key_raises_error(self, monkeypatch):
        """测试未配置 API Key 时抛出异常"""
        monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)
        
        from mainotebook.content.services.moderation_service import ModerationService

        with pytest.raises(ValueError, match="未找到 SILICONFLOW_API_KEY"):
            ModerationService()

    def test_moderate_empty_text(self):
        """测试空文本审核"""
        from mainotebook.content.services.moderation_service import ModerationService
        
        service = ModerationService(api_key="test-key")

        result = service.moderate("")

        assert result["decision"] == "true"
        assert result["confidence"] == 0.0
        assert result["violation_types"] == []

    def test_moderate_whitespace_text(self):
        """测试仅包含空白字符的文本"""
        from mainotebook.content.services.moderation_service import ModerationService
        
        service = ModerationService(api_key="test-key")

        result = service.moderate("   \n\t  ")

        assert result["decision"] == "true"
        assert result["confidence"] == 0.0
        assert result["violation_types"] == []

    @patch("mainotebook.content.services.moderation_service.OpenAI")
    def test_moderate_normal_text(self, mock_openai):
        """测试审核正常文本"""
        from mainotebook.content.services.moderation_service import ModerationService
        
        # Mock OpenAI 响应
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = (
            '{"decision": "true", "confidence": 0.15, "violation_types": []}'
        )

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        service = ModerationService(api_key="test-key")
        result = service.moderate("这是一段正常的文本")

        assert result["decision"] == "true"
        assert result["confidence"] == 0.15
        assert result["violation_types"] == []

    @patch("mainotebook.content.services.moderation_service.OpenAI")
    def test_moderate_violation_text(self, mock_openai):
        """测试审核违规文本"""
        from mainotebook.content.services.moderation_service import ModerationService
        
        # Mock OpenAI 响应
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = (
            '{"decision": "false", "confidence": 0.95, "violation_types": ["porn"]}'
        )

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        service = ModerationService(api_key="test-key")
        result = service.moderate("违规内容")

        assert result["decision"] == "false"
        assert result["confidence"] == 0.95
        assert result["violation_types"] == ["porn"]

    @patch("mainotebook.content.services.moderation_service.OpenAI")
    def test_moderate_unknown_text(self, mock_openai):
        """测试审核不确定文本"""
        from mainotebook.content.services.moderation_service import ModerationService
        
        # Mock OpenAI 响应
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = (
            '{"decision": "unknown", "confidence": 0.65, "violation_types": ["politics"]}'
        )

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        service = ModerationService(api_key="test-key")
        result = service.moderate("疑似违规内容")

        assert result["decision"] == "unknown"
        assert result["confidence"] == 0.65
        assert result["violation_types"] == ["politics"]

    @patch("mainotebook.content.services.moderation_service.OpenAI")
    def test_moderate_invalid_json_response(self, mock_openai):
        """测试无效的 JSON 响应"""
        from mainotebook.content.services.moderation_service import ModerationService
        
        # Mock OpenAI 响应（返回无效 JSON）
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "这不是有效的 JSON"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        service = ModerationService(api_key="test-key")
        result = service.moderate("测试文本")

        # 应该返回默认的不确定结果
        assert result["decision"] == "unknown"
        assert result["confidence"] == 0.5
        assert result["violation_types"] == []

    @patch("mainotebook.content.services.moderation_service.OpenAI")
    def test_moderate_api_exception(self, mock_openai):
        """测试 API 调用异常"""
        from mainotebook.content.services.moderation_service import ModerationService
        
        # Mock OpenAI 抛出异常
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API 错误")
        mock_openai.return_value = mock_client

        service = ModerationService(api_key="test-key")
        result = service.moderate("测试文本")

        # 应该返回默认的不确定结果
        assert result["decision"] == "unknown"
        assert result["confidence"] == 0.5
        assert result["violation_types"] == []

    def test_validate_result_valid(self):
        """测试验证有效的结果"""
        from mainotebook.content.services.moderation_service import ModerationService
        
        service = ModerationService(api_key="test-key")

        valid_result = {
            "decision": "true",
            "confidence": 0.5,
            "violation_types": []
        }

        assert service._validate_result(valid_result) is True

    def test_validate_result_invalid_decision(self):
        """测试验证无效的决策值"""
        from mainotebook.content.services.moderation_service import ModerationService
        
        service = ModerationService(api_key="test-key")

        invalid_result = {
            "decision": "invalid",
            "confidence": 0.5,
            "violation_types": []
        }

        assert service._validate_result(invalid_result) is False

    def test_validate_result_invalid_confidence(self):
        """测试验证无效的置信度"""
        from mainotebook.content.services.moderation_service import ModerationService
        
        service = ModerationService(api_key="test-key")

        # 置信度超出范围
        invalid_result = {
            "decision": "true",
            "confidence": 1.5,
            "violation_types": []
        }

        assert service._validate_result(invalid_result) is False

    def test_get_default_unknown_result(self):
        """测试获取默认不确定结果"""
        from mainotebook.content.services.moderation_service import ModerationService
        
        service = ModerationService(api_key="test-key")

        result = service._get_default_unknown_result()

        assert result["decision"] == "unknown"
        assert result["confidence"] == 0.5
        assert result["violation_types"] == []

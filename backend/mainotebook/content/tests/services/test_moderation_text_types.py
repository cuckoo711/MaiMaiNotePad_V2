"""
ModerationService 新增 text_type（knowledge/persona）单元测试

验证 ModerationService 的 CONTEXT_RULES 包含 knowledge 和 persona 键，
以及使用这两种 text_type 调用时提示词正确生成。

注意：此测试不依赖 Django 配置，仅测试 ModerationService 的核心逻辑。

Validates: Requirements 4.1, 4.2
"""

import pytest


class TestModerationServiceTextTypes:
    """ModerationService knowledge/persona text_type 单元测试"""

    # ---- CONTEXT_RULES 键存在性测试 ----

    def test_context_rules_contains_knowledge_key(self):
        """验证 CONTEXT_RULES 包含 'knowledge' 键"""
        from mainotebook.content.services.moderation_service import ModerationService

        assert "knowledge" in ModerationService.CONTEXT_RULES

    def test_context_rules_contains_persona_key(self):
        """验证 CONTEXT_RULES 包含 'persona' 键"""
        from mainotebook.content.services.moderation_service import ModerationService

        assert "persona" in ModerationService.CONTEXT_RULES

    # ---- knowledge 规则文本内容测试 ----

    def test_knowledge_rules_contain_education_keyword(self):
        """验证 knowledge 规则文本包含知识库相关关键词"""
        from mainotebook.content.services.moderation_service import ModerationService

        rules = ModerationService.CONTEXT_RULES["knowledge"]
        assert "知识库" in rules

    def test_knowledge_rules_contain_academic_keyword(self):
        """验证 knowledge 规则文本包含学术性相关关键词"""
        from mainotebook.content.services.moderation_service import ModerationService

        rules = ModerationService.CONTEXT_RULES["knowledge"]
        assert "学术" in rules

    def test_knowledge_rules_contain_tolerance_keyword(self):
        """验证 knowledge 规则文本包含宽容审核相关关键词"""
        from mainotebook.content.services.moderation_service import ModerationService

        rules = ModerationService.CONTEXT_RULES["knowledge"]
        assert "宽容" in rules

    # ---- persona 规则文本内容测试 ----

    def test_persona_rules_contain_character_keyword(self):
        """验证 persona 规则文本包含角色相关关键词"""
        from mainotebook.content.services.moderation_service import ModerationService

        rules = ModerationService.CONTEXT_RULES["persona"]
        assert "角色" in rules

    def test_persona_rules_contain_fictional_keyword(self):
        """验证 persona 规则文本包含虚构角色相关关键词"""
        from mainotebook.content.services.moderation_service import ModerationService

        rules = ModerationService.CONTEXT_RULES["persona"]
        assert "虚构" in rules

    def test_persona_rules_contain_dialogue_keyword(self):
        """验证 persona 规则文本包含对话示例审核相关关键词"""
        from mainotebook.content.services.moderation_service import ModerationService

        rules = ModerationService.CONTEXT_RULES["persona"]
        assert "对话" in rules

    # ---- _get_system_prompt 提示词生成测试 ----

    def test_get_system_prompt_knowledge_contains_rules(self):
        """验证 _get_system_prompt('knowledge') 返回包含知识库规则的提示词"""
        from mainotebook.content.services.moderation_service import ModerationService

        service = ModerationService(api_key="test-key")
        prompt = service._get_system_prompt("knowledge")

        knowledge_rules = ModerationService.CONTEXT_RULES["knowledge"]
        assert knowledge_rules in prompt

    def test_get_system_prompt_persona_contains_rules(self):
        """验证 _get_system_prompt('persona') 返回包含人设卡规则的提示词"""
        from mainotebook.content.services.moderation_service import ModerationService

        service = ModerationService(api_key="test-key")
        prompt = service._get_system_prompt("persona")

        persona_rules = ModerationService.CONTEXT_RULES["persona"]
        assert persona_rules in prompt

    def test_get_system_prompt_knowledge_contains_base_prompt(self):
        """验证 _get_system_prompt('knowledge') 返回包含基础提示词"""
        from mainotebook.content.services.moderation_service import ModerationService

        service = ModerationService(api_key="test-key")
        prompt = service._get_system_prompt("knowledge")

        assert "内容安全审核员" in prompt

    def test_get_system_prompt_persona_contains_base_prompt(self):
        """验证 _get_system_prompt('persona') 返回包含基础提示词"""
        from mainotebook.content.services.moderation_service import ModerationService

        service = ModerationService(api_key="test-key")
        prompt = service._get_system_prompt("persona")

        assert "内容安全审核员" in prompt

    def test_get_system_prompt_unknown_type_falls_back_to_content(self):
        """验证未知 text_type 回退到 content 规则"""
        from mainotebook.content.services.moderation_service import ModerationService

        service = ModerationService(api_key="test-key")
        prompt = service._get_system_prompt("unknown_type")

        content_rules = ModerationService.CONTEXT_RULES["content"]
        assert content_rules in prompt

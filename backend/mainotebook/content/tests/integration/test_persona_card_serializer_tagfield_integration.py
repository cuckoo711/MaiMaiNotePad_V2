# -*- coding: utf-8 -*-

"""
PersonaCardSerializer TagField 集成测试

验证 PersonaCardSerializer 正确声明了 TagField。
这些测试不依赖数据库迁移，只验证序列化器的字段声明。
"""

import pytest
from mainotebook.content.serializers.persona_card import (
    PersonaCardSerializer,
    PersonaCardCreateSerializer,
    PersonaCardUpdateSerializer
)
from mainotebook.content.serializers.common import TagField


class TestPersonaCardSerializerTagFieldDeclaration:
    """测试 PersonaCardSerializer 的 TagField 声明"""
    
    def test_persona_card_serializer_has_tag_field(self):
        """测试 PersonaCardSerializer 包含 TagField"""
        # 验证序列化器有 tags 字段
        assert 'tags' in PersonaCardSerializer._declared_fields
        
        # 验证 tags 字段是 TagField 类型
        tags_field = PersonaCardSerializer._declared_fields['tags']
        assert isinstance(tags_field, TagField)
        
        # 验证字段配置
        assert tags_field.required is False
        assert tags_field.allow_null is True
    
    def test_persona_card_create_serializer_has_tag_field(self):
        """测试 PersonaCardCreateSerializer 包含 TagField"""
        # 验证序列化器有 tags 字段
        assert 'tags' in PersonaCardCreateSerializer._declared_fields
        
        # 验证 tags 字段是 TagField 类型
        tags_field = PersonaCardCreateSerializer._declared_fields['tags']
        assert isinstance(tags_field, TagField)
        
        # 验证字段配置
        assert tags_field.required is False
        assert tags_field.allow_null is True
    
    def test_persona_card_update_serializer_has_tag_field(self):
        """测试 PersonaCardUpdateSerializer 包含 TagField"""
        # 验证序列化器有 tags 字段
        assert 'tags' in PersonaCardUpdateSerializer._declared_fields
        
        # 验证 tags 字段是 TagField 类型
        tags_field = PersonaCardUpdateSerializer._declared_fields['tags']
        assert isinstance(tags_field, TagField)
        
        # 验证字段配置
        assert tags_field.required is False
        assert tags_field.allow_null is True
    
    def test_tag_field_configuration(self):
        """测试 TagField 的配置参数"""
        tags_field = PersonaCardSerializer._declared_fields['tags']
        
        # 验证 TagField 的常量配置
        assert tags_field.MAX_TAG_LENGTH == 50
        assert tags_field.MAX_TAGS_COUNT == 20

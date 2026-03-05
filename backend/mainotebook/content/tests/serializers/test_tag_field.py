# -*- coding: utf-8 -*-

"""
TagField 单元测试

测试 TagField 序列化器字段的数据验证、转换和标准化功能。

验证需求：10.1, 10.2, 10.3
"""

import pytest
from rest_framework import serializers
from mainotebook.content.serializers.common import TagField


class TestTagFieldArrayParsing:
    """测试数组格式解析"""
    
    def test_parse_valid_array(self):
        """测试解析有效的标签数组"""
        field = TagField()
        result = field.to_internal_value(["标签1", "标签2", "标签3"])
        
        assert result == ["标签1", "标签2", "标签3"]
        assert isinstance(result, list)
    
    def test_parse_single_tag_array(self):
        """测试解析单个标签的数组"""
        field = TagField()
        result = field.to_internal_value(["单个标签"])
        
        assert result == ["单个标签"]
    
    def test_parse_empty_array(self):
        """测试解析空数组"""
        field = TagField()
        result = field.to_internal_value([])
        
        assert result == []


class TestTagFieldStringParsing:
    """测试字符串格式解析（向后兼容）"""
    
    def test_parse_comma_separated_string(self):
        """测试解析逗号分隔的字符串"""
        field = TagField()
        result = field.to_internal_value("标签1,标签2,标签3")
        
        assert result == ["标签1", "标签2", "标签3"]
    
    def test_parse_single_tag_string(self):
        """测试解析单个标签的字符串"""
        field = TagField()
        result = field.to_internal_value("单个标签")
        
        assert result == ["单个标签"]
    
    def test_parse_string_with_spaces(self):
        """测试解析包含空格的字符串"""
        field = TagField()
        result = field.to_internal_value("标签1, 标签2 , 标签3")
        
        assert result == ["标签1", "标签2", "标签3"]
    
    def test_parse_empty_string(self):
        """测试解析空字符串"""
        field = TagField()
        result = field.to_internal_value("")
        
        assert result == []


class TestTagFieldNullHandling:
    """测试空值处理"""
    
    def test_parse_none(self):
        """测试解析 None 值"""
        field = TagField()
        result = field.to_internal_value(None)
        
        assert result == []
    
    def test_parse_empty_string(self):
        """测试解析空字符串"""
        field = TagField()
        result = field.to_internal_value("")
        
        assert result == []
    
    def test_parse_empty_array(self):
        """测试解析空数组"""
        field = TagField()
        result = field.to_internal_value([])
        
        assert result == []


class TestTagFieldNormalization:
    """测试标签标准化（去空格、去重、过滤空字符串）"""
    
    def test_trim_whitespace_in_array(self):
        """测试去除数组中标签的首尾空格"""
        field = TagField()
        result = field.to_internal_value(["  标签1  ", " 标签2 ", "标签3"])
        
        assert result == ["标签1", "标签2", "标签3"]
    
    def test_trim_whitespace_in_string(self):
        """测试去除字符串中标签的首尾空格"""
        field = TagField()
        result = field.to_internal_value("  标签1  ,  标签2  ,  标签3  ")
        
        assert result == ["标签1", "标签2", "标签3"]
    
    def test_remove_duplicates_in_array(self):
        """测试去除数组中的重复标签"""
        field = TagField()
        result = field.to_internal_value(["标签1", "标签2", "标签1", "标签3", "标签2"])
        
        assert result == ["标签1", "标签2", "标签3"]
    
    def test_remove_duplicates_in_string(self):
        """测试去除字符串中的重复标签"""
        field = TagField()
        result = field.to_internal_value("标签1,标签2,标签1,标签3,标签2")
        
        assert result == ["标签1", "标签2", "标签3"]
    
    def test_filter_empty_strings_in_array(self):
        """测试过滤数组中的空字符串"""
        field = TagField()
        result = field.to_internal_value(["标签1", "", "标签2", "  ", "标签3"])
        
        assert result == ["标签1", "标签2", "标签3"]
    
    def test_filter_empty_strings_in_string(self):
        """测试过滤字符串中的空标签（连续逗号）"""
        field = TagField()
        result = field.to_internal_value("标签1,,标签2,  ,标签3")
        
        assert result == ["标签1", "标签2", "标签3"]
    
    def test_combined_normalization(self):
        """测试组合标准化：去空格 + 去重 + 过滤空值"""
        field = TagField()
        result = field.to_internal_value(["  标签1  ", "标签2", "", "  标签1  ", "标签3", "  "])
        
        assert result == ["标签1", "标签2", "标签3"]


class TestTagFieldLengthValidation:
    """测试长度验证"""
    
    def test_single_tag_max_length(self):
        """测试单个标签的最大长度限制（50 字符）"""
        field = TagField()
        valid_tag = "a" * 50
        result = field.to_internal_value([valid_tag])
        
        assert result == [valid_tag]
    
    def test_single_tag_exceeds_max_length(self):
        """测试单个标签超过最大长度"""
        field = TagField()
        invalid_tag = "a" * 51
        
        with pytest.raises(serializers.ValidationError) as exc_info:
            field.to_internal_value([invalid_tag])
        
        assert "超过最大长度" in str(exc_info.value)
        assert "50" in str(exc_info.value)
    
    def test_tags_count_max_limit(self):
        """测试标签数量的最大限制（20 个）"""
        field = TagField()
        valid_tags = [f"标签{i}" for i in range(20)]
        result = field.to_internal_value(valid_tags)
        
        assert len(result) == 20
    
    def test_tags_count_exceeds_max_limit(self):
        """测试标签数量超过最大限制"""
        field = TagField()
        invalid_tags = [f"标签{i}" for i in range(21)]
        
        with pytest.raises(serializers.ValidationError) as exc_info:
            field.to_internal_value(invalid_tags)
        
        assert "超过最大限制" in str(exc_info.value)
        assert "20" in str(exc_info.value)
    
    def test_chinese_tag_length(self):
        """测试中文标签长度计算"""
        field = TagField()
        # 50 个中文字符
        valid_tag = "标" * 50
        result = field.to_internal_value([valid_tag])
        
        assert result == [valid_tag]
    
    def test_chinese_tag_exceeds_length(self):
        """测试中文标签超过长度限制"""
        field = TagField()
        # 51 个中文字符
        invalid_tag = "标" * 51
        
        with pytest.raises(serializers.ValidationError) as exc_info:
            field.to_internal_value([invalid_tag])
        
        assert "超过最大长度" in str(exc_info.value)


class TestTagFieldInvalidTypeValidation:
    """测试无效类型验证"""
    
    def test_reject_integer(self):
        """测试拒绝整数类型"""
        field = TagField()
        
        with pytest.raises(serializers.ValidationError) as exc_info:
            field.to_internal_value(123)
        
        assert "格式错误" in str(exc_info.value)
    
    def test_reject_dict(self):
        """测试拒绝字典类型"""
        field = TagField()
        
        with pytest.raises(serializers.ValidationError) as exc_info:
            field.to_internal_value({"tag": "标签1"})
        
        assert "格式错误" in str(exc_info.value)
    
    def test_reject_non_string_in_array(self):
        """测试拒绝数组中的非字符串元素"""
        field = TagField()
        
        with pytest.raises(serializers.ValidationError) as exc_info:
            field.to_internal_value(["标签1", 123, "标签2"])
        
        assert "必须是字符串类型" in str(exc_info.value)
    
    def test_reject_boolean(self):
        """测试拒绝布尔类型"""
        field = TagField()
        
        with pytest.raises(serializers.ValidationError) as exc_info:
            field.to_internal_value(True)
        
        assert "格式错误" in str(exc_info.value)
    
    def test_reject_float(self):
        """测试拒绝浮点数类型"""
        field = TagField()
        
        with pytest.raises(serializers.ValidationError) as exc_info:
            field.to_internal_value(3.14)
        
        assert "格式错误" in str(exc_info.value)


class TestTagFieldToRepresentation:
    """测试 to_representation 方法（数据库值转换为 API 响应）"""
    
    def test_represent_array(self):
        """测试表示数组格式"""
        field = TagField()
        result = field.to_representation(["标签1", "标签2", "标签3"])
        
        assert result == ["标签1", "标签2", "标签3"]
    
    def test_represent_string_legacy_format(self):
        """测试表示字符串格式（迁移期间的旧数据）"""
        field = TagField()
        result = field.to_representation("标签1,标签2,标签3")
        
        assert result == ["标签1", "标签2", "标签3"]
    
    def test_represent_none(self):
        """测试表示 None 值"""
        field = TagField()
        result = field.to_representation(None)
        
        assert result == []
    
    def test_represent_empty_array(self):
        """测试表示空数组"""
        field = TagField()
        result = field.to_representation([])
        
        assert result == []
    
    def test_represent_array_with_empty_strings(self):
        """测试表示包含空字符串的数组（过滤空值）"""
        field = TagField()
        result = field.to_representation(["标签1", "", "标签2", None, "标签3"])
        
        assert result == ["标签1", "标签2", "标签3"]
    
    def test_represent_string_with_spaces(self):
        """测试表示包含空格的字符串（去除空格）"""
        field = TagField()
        result = field.to_representation("  标签1  ,  标签2  ,  标签3  ")
        
        assert result == ["标签1", "标签2", "标签3"]


class TestTagFieldEdgeCases:
    """测试边缘情况"""
    
    def test_only_whitespace_string(self):
        """测试只包含空格的字符串"""
        field = TagField()
        result = field.to_internal_value("   ")
        
        assert result == []
    
    def test_only_commas_string(self):
        """测试只包含逗号的字符串"""
        field = TagField()
        result = field.to_internal_value(",,,")
        
        assert result == []
    
    def test_only_whitespace_in_array(self):
        """测试数组中只包含空格的元素"""
        field = TagField()
        result = field.to_internal_value(["   ", "  ", ""])
        
        assert result == []
    
    def test_mixed_valid_and_empty(self):
        """测试混合有效标签和空值"""
        field = TagField()
        result = field.to_internal_value(["标签1", "", "   ", "标签2", ",", "标签3"])
        
        assert result == ["标签1", "标签2", ",", "标签3"]
    
    def test_unicode_tags(self):
        """测试 Unicode 标签（表情符号等）"""
        field = TagField()
        result = field.to_internal_value(["标签1", "🎉", "标签2", "😊"])
        
        assert result == ["标签1", "🎉", "标签2", "😊"]
    
    def test_special_characters_in_tags(self):
        """测试标签中的特殊字符"""
        field = TagField()
        result = field.to_internal_value(["C++", "C#", ".NET", "Node.js"])
        
        assert result == ["C++", "C#", ".NET", "Node.js"]
    
    def test_preserve_order(self):
        """测试保持标签顺序（去重时保留首次出现的顺序）"""
        field = TagField()
        result = field.to_internal_value(["标签3", "标签1", "标签2", "标签1", "标签3"])
        
        assert result == ["标签3", "标签1", "标签2"]

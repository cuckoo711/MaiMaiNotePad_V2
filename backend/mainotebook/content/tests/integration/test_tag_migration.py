"""标签迁移测试

测试标签字段从字符串格式迁移到数组格式的功能。
这些测试验证迁移脚本中使用的转换逻辑。

需求：10.1, 10.2
"""

from typing import List, Union
from django.test import TestCase
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase as HypothesisTestCase
from mainotebook.content.models import PersonaCard, KnowledgeBase
from mainotebook.system.models import Users


def parse_tags_string_to_array(tags_str: Union[str, List[str], None]) -> List[str]:
    """将标签字符串转换为数组（模拟迁移逻辑）
    
    这个函数复制了迁移脚本 0012_convert_tags_data.py 中的 parse_tags 逻辑。
    
    Args:
        tags_str: 标签数据，可能是字符串、数组或 None
        
    Returns:
        list: 标签数组
    """
    # 如果已经是数组，直接返回
    if isinstance(tags_str, list):
        return tags_str
    
    # 如果是 None 或空字符串，返回空数组
    if not tags_str:
        return []
    
    # 如果是字符串，按逗号分割并去除空格
    if isinstance(tags_str, str):
        tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
        return tags
    
    # 其他情况返回空数组
    return []


def tags_array_to_string(tags_array: Union[List[str], str, None]) -> str:
    """将标签数组转换为字符串（模拟回滚逻辑）
    
    这个函数复制了迁移脚本 0012_convert_tags_data.py 中的 tags_to_string 逻辑。
    
    Args:
        tags_array: 标签数据，可能是数组、字符串或 None
        
    Returns:
        str: 逗号分隔的标签字符串
    """
    # 如果已经是字符串，直接返回
    if isinstance(tags_array, str):
        return tags_array
    
    # 如果是 None 或空数组，返回空字符串
    if not tags_array:
        return ''
    
    # 如果是数组，用逗号连接
    if isinstance(tags_array, list):
        return ','.join(str(tag) for tag in tags_array if tag)
    
    # 其他情况返回空字符串
    return ''


class TestTagMigrationFunctions(TestCase):
    """标签迁移函数单元测试"""
    
    def test_parse_tags_simple_string(self):
        """测试解析简单标签字符串"""
        result = parse_tags_string_to_array("标签1,标签2,标签3")
        assert result == ["标签1", "标签2", "标签3"]
    
    def test_parse_tags_with_spaces(self):
        """测试解析带空格的标签字符串"""
        result = parse_tags_string_to_array("  标签1  , 标签2 ,标签3  ")
        assert result == ["标签1", "标签2", "标签3"], "应该去除首尾空格"
    
    def test_parse_tags_with_empty_items(self):
        """测试解析包含空项的标签字符串"""
        result = parse_tags_string_to_array("标签1,,标签2,,,标签3")
        assert result == ["标签1", "标签2", "标签3"], "应该过滤空项"
    
    def test_parse_tags_empty_string(self):
        """测试解析空字符串"""
        result = parse_tags_string_to_array("")
        assert result == [], "空字符串应该转换为空数组"
    
    def test_parse_tags_none(self):
        """测试解析 None"""
        result = parse_tags_string_to_array(None)
        assert result == [], "None 应该转换为空数组"
    
    def test_parse_tags_already_array(self):
        """测试解析已经是数组的标签（幂等性）"""
        result = parse_tags_string_to_array(["标签1", "标签2", "标签3"])
        assert result == ["标签1", "标签2", "标签3"], "已经是数组的应该保持不变"
    
    def test_tags_to_string_simple_array(self):
        """测试将数组转换为字符串"""
        result = tags_array_to_string(["标签1", "标签2", "标签3"])
        assert result == "标签1,标签2,标签3"
    
    def test_tags_to_string_empty_array(self):
        """测试将空数组转换为字符串"""
        result = tags_array_to_string([])
        assert result == '', "空数组应该转换为空字符串"
    
    def test_tags_to_string_none(self):
        """测试将 None 转换为字符串"""
        result = tags_array_to_string(None)
        assert result == '', "None 应该转换为空字符串"
    
    def test_tags_to_string_already_string(self):
        """测试转换已经是字符串的标签（幂等性）"""
        result = tags_array_to_string("标签1,标签2,标签3")
        assert result == "标签1,标签2,标签3", "已经是字符串的应该保持不变"
    
    def test_roundtrip_migration_simple(self):
        """测试往返迁移（简单情况）
        
        Feature: tags-array-migration, Property 9: 迁移数据往返一致性
        """
        original_tags = "标签1,标签2,标签3"
        
        # 字符串 → 数组（前向迁移）
        tags_array = parse_tags_string_to_array(original_tags)
        
        # 数组 → 字符串（回滚）
        tags_string = tags_array_to_string(tags_array)
        
        # 验证等价
        assert tags_string == original_tags, "往返迁移应该保持一致"
    
    def test_roundtrip_migration_with_spaces(self):
        """测试往返迁移（带空格）
        
        Feature: tags-array-migration, Property 9: 迁移数据往返一致性
        """
        original_tags = "  标签1  , 标签2 ,标签3  "
        
        # 字符串 → 数组（前向迁移）
        tags_array = parse_tags_string_to_array(original_tags)
        
        # 数组 → 字符串（回滚）
        tags_string = tags_array_to_string(tags_array)
        
        # 标准化的原始字符串
        normalized_original = "标签1,标签2,标签3"
        
        # 验证等价（标准化后）
        assert tags_string == normalized_original, "往返迁移应该得到标准化的等价字符串"
    
    def test_roundtrip_migration_with_empty_items(self):
        """测试往返迁移（包含空项）
        
        Feature: tags-array-migration, Property 9: 迁移数据往返一致性
        """
        original_tags = "标签1,,标签2,,,标签3"
        
        # 字符串 → 数组（前向迁移）
        tags_array = parse_tags_string_to_array(original_tags)
        
        # 数组 → 字符串（回滚）
        tags_string = tags_array_to_string(tags_array)
        
        # 标准化的原始字符串（去除空项）
        normalized_original = "标签1,标签2,标签3"
        
        # 验证等价（标准化后）
        assert tags_string == normalized_original, "往返迁移应该过滤空项"
    
    def test_roundtrip_migration_empty_string(self):
        """测试往返迁移（空字符串）
        
        Feature: tags-array-migration, Property 9: 迁移数据往返一致性
        """
        original_tags = ""
        
        # 字符串 → 数组（前向迁移）
        tags_array = parse_tags_string_to_array(original_tags)
        
        # 数组 → 字符串（回滚）
        tags_string = tags_array_to_string(tags_array)
        
        # 验证等价
        assert tags_string == original_tags, "空字符串往返迁移应该保持一致"


class TestTagMigrationProperties:
    """标签迁移属性测试
    
    使用 Hypothesis 进行基于属性的测试，验证迁移逻辑在各种输入下的正确性。
    注意：这些测试不依赖数据库，只测试迁移函数的逻辑正确性。
    """
    
    @given(st.lists(
        st.text(
            alphabet=st.characters(
                blacklist_categories=('Cs',),
                blacklist_characters=','
            ),
            min_size=1,
            max_size=50
        ).filter(lambda x: x.strip()),
        min_size=0,
        max_size=20
    ))
    @settings(max_examples=100, deadline=None)
    def test_property_9_roundtrip_consistency(self, tags_list: List[str]):
        """属性测试：迁移数据往返一致性
        
        Feature: tags-array-migration, Property 9: 迁移数据往返一致性
        
        对于任意标签字符串，经过"字符串→数组"迁移后再"数组→字符串"回滚，
        应该得到标准化的等价字符串。
        """
        # 构造原始标签字符串
        original_tags = ','.join(tags_list)
        
        # 前向迁移：字符串 → 数组
        tags_array = parse_tags_string_to_array(original_tags)
        
        # 回滚：数组 → 字符串
        tags_string = tags_array_to_string(tags_array)
        
        # 标准化原始字符串（去除空格、空项）
        normalized_original = ','.join([tag.strip() for tag in original_tags.split(',') if tag.strip()]) if original_tags else ''
        
        # 验证往返一致性
        assert tags_string == normalized_original, \
            f"往返迁移应该保持一致：原始='{normalized_original}', 结果='{tags_string}'"

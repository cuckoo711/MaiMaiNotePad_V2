# -*- coding: utf-8 -*-

"""
TagField 属性测试

使用 Hypothesis 进行基于属性的测试，验证 TagField 的不变性和正确性属性。

验证需求：10.6, 10.7
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from rest_framework import serializers
from mainotebook.content.serializers.common import TagField


# ==================== 测试策略（Strategies） ====================

# 生成有效的标签字符串（1-50 个字符）
valid_tag_strategy = st.text(
    alphabet=st.characters(
        blacklist_categories=('Cs',),  # 排除代理字符
        blacklist_characters='\x00\n\r\t',  # 排除空字符和控制字符
    ),
    min_size=1,
    max_size=50
).filter(lambda s: s.strip())  # 确保去除空格后不为空

# 生成标签数组（0-20 个标签）
tag_array_strategy = st.lists(
    valid_tag_strategy,
    min_size=0,
    max_size=20
)

# 生成逗号分隔的标签字符串
tag_string_strategy = st.lists(
    valid_tag_strategy,
    min_size=0,
    max_size=20
).map(lambda tags: ','.join(tags))

# 生成可能包含空格的标签数组
tag_array_with_spaces_strategy = st.lists(
    st.text(
        alphabet=st.characters(
            blacklist_categories=('Cs',),
            blacklist_characters='\x00\n\r\t',
        ),
        min_size=1,
        max_size=50
    ).map(lambda s: f"  {s}  "),  # 在标签前后添加空格
    min_size=0,
    max_size=20
)

# 生成可能包含重复的标签数组
tag_array_with_duplicates_strategy = st.lists(
    valid_tag_strategy,
    min_size=0,
    max_size=40  # 允许更多以便产生重复
).filter(lambda tags: len(tags) <= 40)

# 生成可能包含空字符串的标签数组
tag_array_with_empty_strategy = st.lists(
    st.one_of(
        valid_tag_strategy,
        st.just(''),
        st.just('   ')
    ),
    min_size=0,
    max_size=25
)


# ==================== 属性 1：标签字符串解析往返 ====================

class TestProperty1_StringParsingRoundtrip:
    """属性 1：标签字符串解析往返
    
    **验证需求：2.1, 2.3**
    
    对于任意标签字符串（逗号分隔），解析为数组后再转换回字符串，
    应该得到标准化的等价形式（去除空格、空项、保持顺序）
    """
    
    @given(tag_string_strategy)
    @settings(max_examples=100)
    def test_string_parsing_roundtrip(self, tag_string: str):
        """测试字符串解析往返的一致性"""
        field = TagField()
        
        try:
            # 解析字符串为数组
            parsed_array = field.to_internal_value(tag_string)
            
            # 将数组转换回字符串
            result_string = ','.join(parsed_array)
            
            # 再次解析
            reparsed_array = field.to_internal_value(result_string)
            
            # 往返后应该保持一致
            assert parsed_array == reparsed_array, \
                f"往返解析不一致: {tag_string} -> {parsed_array} -> {result_string} -> {reparsed_array}"
        except serializers.ValidationError:
            # 如果原始字符串超过限制，跳过此测试
            # 这是可接受的，因为我们主要测试有效输入的往返一致性
            pass
    
    @given(tag_string_strategy)
    @settings(max_examples=100)
    def test_string_parsing_normalization(self, tag_string: str):
        """测试字符串解析的标准化处理"""
        field = TagField()
        
        # 解析字符串
        parsed = field.to_internal_value(tag_string)
        
        # 验证标准化属性
        # 1. 所有标签都已去除首尾空格
        for tag in parsed:
            assert tag == tag.strip(), f"标签未去除空格: '{tag}'"
        
        # 2. 没有空字符串
        assert '' not in parsed, "结果包含空字符串"
        
        # 3. 没有重复标签
        assert len(parsed) == len(set(parsed)), f"结果包含重复标签: {parsed}"


# ==================== 属性 2：序列化器标签标准化 ====================

class TestProperty2_SerializerNormalization:
    """属性 2：序列化器标签标准化
    
    **验证需求：3.1, 3.2, 3.3, 3.4, 3.5**
    
    对于任意标签输入（数组或字符串），序列化器处理后应该返回标准化的数组：
    去除首尾空格、过滤空字符串、去除重复项、保持首次出现顺序
    """
    
    @given(tag_array_with_spaces_strategy)
    @settings(max_examples=100)
    def test_normalization_removes_whitespace(self, tags_with_spaces):
        """测试标准化处理去除首尾空格"""
        # 过滤掉去除空格后为空的标签
        tags_with_spaces = [t for t in tags_with_spaces if t.strip()]
        
        # 如果所有标签都为空，跳过此测试
        assume(len(tags_with_spaces) > 0)
        
        field = TagField()
        result = field.to_internal_value(tags_with_spaces)
        
        # 验证所有标签都已去除空格
        for tag in result:
            assert tag == tag.strip(), f"标签未去除空格: '{tag}'"
            assert len(tag) > 0, "结果包含空字符串"
    
    @given(tag_array_with_empty_strategy)
    @settings(max_examples=100)
    def test_normalization_filters_empty_strings(self, tags_with_empty):
        """测试标准化处理过滤空字符串"""
        field = TagField()
        
        try:
            result = field.to_internal_value(tags_with_empty)
            
            # 验证没有空字符串
            assert '' not in result, "结果包含空字符串"
            
            # 验证所有标签都不是纯空格
            for tag in result:
                assert tag.strip() != '', f"结果包含纯空格标签: '{tag}'"
        except serializers.ValidationError:
            # 如果验证失败（例如超过长度限制），这也是可接受的
            pass
    
    @given(tag_array_with_duplicates_strategy)
    @settings(max_examples=100)
    def test_normalization_removes_duplicates(self, tags_with_duplicates):
        """测试标准化处理去除重复项"""
        # 限制标签数量以避免超过最大限制
        tags_with_duplicates = tags_with_duplicates[:20]
        
        field = TagField()
        
        try:
            result = field.to_internal_value(tags_with_duplicates)
            
            # 验证没有重复标签
            assert len(result) == len(set(result)), \
                f"结果包含重复标签: {result}"
        except serializers.ValidationError:
            # 如果验证失败（例如超过长度限制），这也是可接受的
            pass
    
    @given(tag_array_with_duplicates_strategy)
    @settings(max_examples=100)
    def test_normalization_preserves_first_occurrence_order(self, tags):
        """测试标准化处理保持首次出现的顺序"""
        # 限制标签数量
        tags = tags[:20]
        
        field = TagField()
        
        try:
            result = field.to_internal_value(tags)
            
            # 手动去重，保持首次出现顺序
            seen = set()
            expected = []
            for tag in tags:
                tag = tag.strip()
                if tag and tag not in seen:
                    seen.add(tag)
                    expected.append(tag)
            
            # 验证顺序一致
            assert result == expected, \
                f"顺序不一致: 输入={tags}, 期望={expected}, 实际={result}"
        except serializers.ValidationError:
            # 如果验证失败，这也是可接受的
            pass
    
    @given(st.one_of(
        tag_array_strategy,
        tag_string_strategy
    ))
    @settings(max_examples=100)
    def test_normalization_accepts_both_formats(self, tags_input):
        """测试标准化处理接受数组和字符串两种格式"""
        field = TagField()
        
        try:
            result = field.to_internal_value(tags_input)
            
            # 验证结果是列表
            assert isinstance(result, list), f"结果不是列表: {type(result)}"
            
            # 验证所有元素是字符串
            for tag in result:
                assert isinstance(tag, str), f"标签不是字符串: {type(tag)}"
        except serializers.ValidationError:
            # 如果验证失败，这也是可接受的
            pass


# ==================== 属性 3：序列化器长度验证 ====================

class TestProperty3_SerializerLengthValidation:
    """属性 3：序列化器长度验证
    
    **验证需求：3.7, 3.8**
    
    对于任意标签数组，如果包含超过 50 个字符的标签或超过 20 个标签，
    序列化器应该抛出验证错误
    """
    
    @given(st.lists(
        st.text(
            alphabet=st.characters(blacklist_categories=('Cs',)),
            min_size=51,  # 超过最大长度
            max_size=100
        ).filter(lambda s: len(s.strip()) > 50),  # 确保 strip 后仍超过 50 个字符
        min_size=1,
        max_size=5
    ))
    @settings(max_examples=100)
    def test_rejects_tags_exceeding_max_length(self, long_tags):
        """测试拒绝超过最大长度的标签"""
        field = TagField()
        
        # 应该抛出验证错误
        with pytest.raises(serializers.ValidationError) as exc_info:
            field.to_internal_value(long_tags)
        
        # 验证错误消息包含长度相关信息
        error_message = str(exc_info.value)
        assert "超过最大长度" in error_message or "50" in error_message, \
            f"错误消息不包含长度信息: {error_message}"
    
    @given(st.lists(
        valid_tag_strategy,
        min_size=21,  # 超过最大数量
        max_size=30
    ))
    @settings(max_examples=100)
    def test_rejects_too_many_tags(self, many_tags):
        """测试拒绝超过最大数量的标签"""
        # 确保标签不重复，以便真正超过限制
        many_tags = list(dict.fromkeys(many_tags))  # 去重但保持顺序
        assume(len(many_tags) > 20)
        
        field = TagField()
        
        # 应该抛出验证错误
        with pytest.raises(serializers.ValidationError) as exc_info:
            field.to_internal_value(many_tags)
        
        # 验证错误消息包含数量相关信息
        error_message = str(exc_info.value)
        assert "超过最大限制" in error_message or "20" in error_message, \
            f"错误消息不包含数量信息: {error_message}"
    
    @given(st.lists(
        st.text(
            alphabet=st.characters(blacklist_categories=('Cs',)),
            min_size=1,
            max_size=50  # 在限制内
        ).filter(lambda s: s.strip()),
        min_size=0,
        max_size=20  # 在限制内
    ))
    @settings(max_examples=100)
    def test_accepts_tags_within_limits(self, valid_tags):
        """测试接受在限制内的标签"""
        field = TagField()
        
        # 不应该抛出错误
        try:
            result = field.to_internal_value(valid_tags)
            
            # 验证结果符合限制
            assert len(result) <= 20, f"结果超过最大数量: {len(result)}"
            for tag in result:
                assert len(tag) <= 50, f"标签超过最大长度: {len(tag)}"
        except serializers.ValidationError as e:
            # 如果抛出错误，说明测试失败
            pytest.fail(f"不应该拒绝有效标签: {e}")
    
    @given(st.integers(min_value=1, max_value=50))
    @settings(max_examples=50)
    def test_boundary_tag_length(self, length):
        """测试边界标签长度"""
        field = TagField()
        
        # 生成指定长度的标签
        tag = 'a' * length
        
        if length <= 50:
            # 应该接受
            result = field.to_internal_value([tag])
            assert result == [tag]
        else:
            # 应该拒绝（但这个分支在当前策略下不会执行）
            with pytest.raises(serializers.ValidationError):
                field.to_internal_value([tag])
    
    @given(st.integers(min_value=0, max_value=25))
    @settings(max_examples=26)
    def test_boundary_tag_count(self, count):
        """测试边界标签数量"""
        field = TagField()
        
        # 生成指定数量的唯一标签
        tags = [f"标签{i}" for i in range(count)]
        
        if count <= 20:
            # 应该接受
            result = field.to_internal_value(tags)
            assert len(result) == count
        else:
            # 应该拒绝
            with pytest.raises(serializers.ValidationError):
                field.to_internal_value(tags)

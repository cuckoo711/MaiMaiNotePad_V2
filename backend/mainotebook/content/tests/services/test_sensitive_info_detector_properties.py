"""敏感信息检测服务属性测试

使用 Hypothesis 进行基于属性的测试，验证敏感信息检测服务的正确性属性。

**验证需求：8.1, 8.2, 8.4**

属性列表：
- 属性 26: 敏感信息检测准确性
- 属性 27: 敏感信息位置记录
"""

import random
from hypothesis import given, settings, strategies as st, assume
from hypothesis.extra.django import TestCase

from mainotebook.content.services.sensitive_info_detector_service import SensitiveInfoDetectorService


# 配置 Hypothesis
settings.register_profile("default", max_examples=100, deadline=None)
settings.load_profile("default")


# 生成策略
def digit_string_strategy(min_digits: int, max_digits: int):
    """生成指定位数的数字字符串
    
    Args:
        min_digits: 最小位数
        max_digits: 最大位数
        
    Returns:
        Strategy: 数字字符串生成策略
    """
    return st.integers(min_value=min_digits, max_value=max_digits).flatmap(
        lambda n: st.text(
            alphabet='0123456789',
            min_size=n,
            max_size=n
        )
    )


def text_without_long_digits_strategy():
    """生成不包含 5-11 位连续数字的文本
    
    Returns:
        Strategy: 文本生成策略
    """
    return st.text(
        alphabet=st.characters(
            whitelist_categories=('Ll', 'Lu', 'Zs', 'Po'),
            blacklist_characters='0123456789'
        ),
        min_size=0,
        max_size=100
    )


def section_name_strategy():
    """生成配置块名称
    
    Returns:
        Strategy: 配置块名称生成策略
    """
    return st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._',
        min_size=1,
        max_size=30
    ).filter(lambda x: x and x[0].isalpha())


def key_name_strategy():
    """生成配置键名
    
    Returns:
        Strategy: 配置键名生成策略
    """
    return st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_',
        min_size=1,
        max_size=30
    ).filter(lambda x: x and x[0].isalpha())


class SensitiveInfoDetectorPropertiesTest(TestCase):
    """敏感信息检测服务属性测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.detector = SensitiveInfoDetectorService()
    
    # ========== 属性 26: 敏感信息检测准确性 ==========
    
    @given(
        digit_count=st.integers(min_value=5, max_value=11),
        prefix_text=text_without_long_digits_strategy(),
        suffix_text=text_without_long_digits_strategy(),
        section=section_name_strategy(),
        key=key_name_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_26_sensitive_info_detection_accuracy_positive(
        self,
        digit_count,
        prefix_text,
        suffix_text,
        section,
        key
    ):
        """属性 26: 敏感信息检测准确性（正向测试）
        
        Feature: persona-card-upload, Property 26: 敏感信息检测准确性
        **验证需求：8.1, 8.2**
        
        对于任意配置项的值，检测器应识别所有 5-11 位连续数字为敏感信息。
        
        本测试验证：当值中包含 5-11 位连续数字时，检测器应该检测到。
        """
        # 生成指定位数的数字
        sensitive_number = ''.join([str(random.randint(0, 9)) for _ in range(digit_count)])
        
        # 确保数字前后有空格或标点，形成单词边界
        test_value = f"{prefix_text} {sensitive_number} {suffix_text}"
        
        # 构建配置项
        configs = [
            {
                'section': section,
                'key': key,
                'value': test_value
            }
        ]
        
        # 检测敏感信息
        result = self.detector.detect(configs)
        
        # 验证：应该检测到敏感信息
        self.assertGreater(
            len(result),
            0,
            f"应该检测到 {digit_count} 位数字 {sensitive_number}"
        )
        
        # 验证：检测到的敏感数字应该包含我们插入的数字
        found = False
        for item in result:
            if sensitive_number in item['matches']:
                found = True
                break
        
        self.assertTrue(
            found,
            f"检测结果应包含 {digit_count} 位数字 {sensitive_number}，但实际检测到：{result}"
        )
    
    @given(
        digit_count=st.one_of(
            st.integers(min_value=1, max_value=4),
            st.integers(min_value=12, max_value=20)
        ),
        prefix_text=text_without_long_digits_strategy(),
        suffix_text=text_without_long_digits_strategy(),
        section=section_name_strategy(),
        key=key_name_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_26_sensitive_info_detection_accuracy_negative(
        self,
        digit_count,
        prefix_text,
        suffix_text,
        section,
        key
    ):
        """属性 26: 敏感信息检测准确性（负向测试）
        
        Feature: persona-card-upload, Property 26: 敏感信息检测准确性
        **验证需求：8.1, 8.2**
        
        对于任意配置项的值，检测器不应将 4 位及以下或 12 位及以上的数字识别为敏感信息。
        
        本测试验证：当值中只包含 1-4 位或 12+ 位连续数字时，检测器不应该检测到。
        """
        # 生成指定位数的数字
        non_sensitive_number = ''.join([str(random.randint(0, 9)) for _ in range(digit_count)])
        
        # 确保数字前后有空格或标点，形成单词边界
        test_value = f"{prefix_text} {non_sensitive_number} {suffix_text}"
        
        # 构建配置项
        configs = [
            {
                'section': section,
                'key': key,
                'value': test_value
            }
        ]
        
        # 检测敏感信息
        result = self.detector.detect(configs)
        
        # 验证：不应该检测到这个数字
        for item in result:
            self.assertNotIn(
                non_sensitive_number,
                item['matches'],
                f"不应该检测到 {digit_count} 位数字 {non_sensitive_number}"
            )
    
    @given(
        digit_counts=st.lists(
            st.integers(min_value=5, max_value=11),
            min_size=1,
            max_size=5
        ),
        section=section_name_strategy(),
        key=key_name_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_26_multiple_sensitive_numbers_detection(
        self,
        digit_counts,
        section,
        key
    ):
        """属性 26: 敏感信息检测准确性（多个敏感数字）
        
        Feature: persona-card-upload, Property 26: 敏感信息检测准确性
        **验证需求：8.1, 8.2**
        
        对于包含多个 5-11 位连续数字的配置项值，检测器应识别所有敏感数字。
        """
        # 生成多个敏感数字
        sensitive_numbers = []
        for count in digit_counts:
            number = ''.join([str(random.randint(0, 9)) for _ in range(count)])
            sensitive_numbers.append(number)
        
        # 构建包含多个敏感数字的值
        test_value = ' '.join(f"QQ{i}: {num}" for i, num in enumerate(sensitive_numbers))
        
        # 构建配置项
        configs = [
            {
                'section': section,
                'key': key,
                'value': test_value
            }
        ]
        
        # 检测敏感信息
        result = self.detector.detect(configs)
        
        # 验证：应该检测到至少一个配置项
        self.assertGreater(
            len(result),
            0,
            f"应该检测到包含敏感信息的配置项"
        )
        
        # 验证：所有敏感数字都应该被检测到
        detected_numbers = []
        for item in result:
            detected_numbers.extend(item['matches'])
        
        for number in sensitive_numbers:
            self.assertIn(
                number,
                detected_numbers,
                f"应该检测到敏感数字 {number}，但实际检测到：{detected_numbers}"
            )
    
    @given(
        text=text_without_long_digits_strategy(),
        section=section_name_strategy(),
        key=key_name_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_26_no_false_positives(
        self,
        text,
        section,
        key
    ):
        """属性 26: 敏感信息检测准确性（无误报）
        
        Feature: persona-card-upload, Property 26: 敏感信息检测准确性
        **验证需求：8.1, 8.2**
        
        对于不包含 5-11 位连续数字的配置项值，检测器不应报告任何敏感信息。
        """
        # 跳过空文本
        assume(text.strip())
        
        # 构建配置项
        configs = [
            {
                'section': section,
                'key': key,
                'value': text
            }
        ]
        
        # 检测敏感信息
        result = self.detector.detect(configs)
        
        # 验证：不应该检测到任何敏感信息
        self.assertEqual(
            len(result),
            0,
            f"不应该在文本 '{text}' 中检测到敏感信息，但检测到：{result}"
        )
    
    @given(
        digit_count=st.integers(min_value=5, max_value=11),
        section=section_name_strategy(),
        key=key_name_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_26_word_boundary_detection(
        self,
        digit_count,
        section,
        key
    ):
        """属性 26: 敏感信息检测准确性（单词边界）
        
        Feature: persona-card-upload, Property 26: 敏感信息检测准确性
        **验证需求：8.1, 8.2**
        
        检测器应使用单词边界匹配，只检测独立的数字，不检测嵌入在字母中的数字。
        """
        # 生成敏感数字
        sensitive_number = ''.join([str(random.randint(0, 9)) for _ in range(digit_count)])
        
        # 测试场景 1：数字前后有字母（不应检测）
        embedded_value = f"abc{sensitive_number}def"
        configs_embedded = [
            {
                'section': section,
                'key': key,
                'value': embedded_value
            }
        ]
        
        result_embedded = self.detector.detect(configs_embedded)
        
        # 验证：嵌入在字母中的数字不应被检测
        self.assertEqual(
            len(result_embedded),
            0,
            f"嵌入在字母中的数字 {sensitive_number} 不应被检测"
        )
        
        # 测试场景 2：数字前后有空格（应检测）
        spaced_value = f"abc {sensitive_number} def"
        configs_spaced = [
            {
                'section': section,
                'key': key,
                'value': spaced_value
            }
        ]
        
        result_spaced = self.detector.detect(configs_spaced)
        
        # 验证：独立的数字应被检测
        self.assertGreater(
            len(result_spaced),
            0,
            f"独立的数字 {sensitive_number} 应被检测"
        )
    
    # ========== 属性 27: 敏感信息位置记录 ==========
    
    @given(
        digit_count=st.integers(min_value=5, max_value=11),
        section=section_name_strategy(),
        key=key_name_strategy(),
        prefix_text=text_without_long_digits_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_27_sensitive_info_location_recording(
        self,
        digit_count,
        section,
        key,
        prefix_text
    ):
        """属性 27: 敏感信息位置记录
        
        Feature: persona-card-upload, Property 27: 敏感信息位置记录
        **验证需求：8.4**
        
        对于任意检测到的敏感信息，系统应记录其所在的配置项路径（section.key）。
        """
        # 生成敏感数字
        sensitive_number = ''.join([str(random.randint(0, 9)) for _ in range(digit_count)])
        
        # 构建包含敏感数字的值
        test_value = f"{prefix_text} {sensitive_number}"
        
        # 构建配置项
        configs = [
            {
                'section': section,
                'key': key,
                'value': test_value
            }
        ]
        
        # 检测敏感信息
        result = self.detector.detect(configs)
        
        # 验证：应该检测到敏感信息
        self.assertGreater(
            len(result),
            0,
            f"应该检测到敏感信息"
        )
        
        # 验证：检测结果应包含正确的配置项路径
        item = result[0]
        
        # 验证：section 字段应正确
        self.assertEqual(
            item['section'],
            section,
            f"section 字段应为 {section}"
        )
        
        # 验证：key 字段应正确
        self.assertEqual(
            item['key'],
            key,
            f"key 字段应为 {key}"
        )
        
        # 验证：path 字段应为 section.key 格式
        expected_path = f"{section}.{key}"
        self.assertEqual(
            item['path'],
            expected_path,
            f"path 字段应为 {expected_path}"
        )
        
        # 验证：value 字段应包含原始值
        self.assertEqual(
            item['value'],
            test_value,
            f"value 字段应包含原始值"
        )
        
        # 验证：matches 字段应包含检测到的数字
        self.assertIn(
            sensitive_number,
            item['matches'],
            f"matches 字段应包含 {sensitive_number}"
        )
    
    @given(
        configs_data=st.lists(
            st.tuples(
                section_name_strategy(),
                key_name_strategy(),
                st.integers(min_value=5, max_value=11)
            ),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_27_multiple_locations_recording(self, configs_data):
        """属性 27: 敏感信息位置记录（多个位置）
        
        Feature: persona-card-upload, Property 27: 敏感信息位置记录
        **验证需求：8.4**
        
        对于多个配置项中的敏感信息，系统应记录所有位置。
        """
        # 构建多个包含敏感信息的配置项
        configs = []
        expected_paths = []
        
        for section, key, digit_count in configs_data:
            sensitive_number = ''.join([str(random.randint(0, 9)) for _ in range(digit_count)])
            configs.append({
                'section': section,
                'key': key,
                'value': f"QQ: {sensitive_number}"
            })
            expected_paths.append(f"{section}.{key}")
        
        # 检测敏感信息
        result = self.detector.detect(configs)
        
        # 验证：应该检测到所有配置项
        self.assertEqual(
            len(result),
            len(configs),
            f"应该检测到 {len(configs)} 个包含敏感信息的配置项"
        )
        
        # 验证：所有路径都应该被记录
        detected_paths = [item['path'] for item in result]
        
        for expected_path in expected_paths:
            self.assertIn(
                expected_path,
                detected_paths,
                f"应该记录路径 {expected_path}"
            )
    
    @given(
        section=section_name_strategy(),
        key=key_name_strategy(),
        digit_count=st.integers(min_value=5, max_value=11)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_27_location_format_consistency(
        self,
        section,
        key,
        digit_count
    ):
        """属性 27: 敏感信息位置记录（格式一致性）
        
        Feature: persona-card-upload, Property 27: 敏感信息位置记录
        **验证需求：8.4**
        
        对于任意检测到的敏感信息，路径格式应始终为 "section.key"。
        """
        # 生成敏感数字
        sensitive_number = ''.join([str(random.randint(0, 9)) for _ in range(digit_count)])
        
        # 构建配置项
        configs = [
            {
                'section': section,
                'key': key,
                'value': sensitive_number
            }
        ]
        
        # 检测敏感信息
        result = self.detector.detect(configs)
        
        # 验证：应该检测到敏感信息
        self.assertGreater(len(result), 0)
        
        # 验证：路径应为 section.key 格式
        item = result[0]
        expected_path = f"{section}.{key}"
        self.assertEqual(
            item['path'],
            expected_path,
            f"路径应为 {expected_path}"
        )
        
        # 验证：路径应包含 section 和 key
        self.assertEqual(item['section'], section, f"section 字段应为 {section}")
        self.assertEqual(item['key'], key, f"key 字段应为 {key}")
    
    @given(
        key=key_name_strategy(),
        digit_count=st.integers(min_value=5, max_value=11)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_27_empty_section_location(self, key, digit_count):
        """属性 27: 敏感信息位置记录（空 section）
        
        Feature: persona-card-upload, Property 27: 敏感信息位置记录
        **验证需求：8.4**
        
        对于顶层配置项（section 为空），路径应只包含 key。
        """
        # 生成敏感数字
        sensitive_number = ''.join([str(random.randint(0, 9)) for _ in range(digit_count)])
        
        # 构建顶层配置项（section 为空）
        configs = [
            {
                'section': '',
                'key': key,
                'value': sensitive_number
            }
        ]
        
        # 检测敏感信息
        result = self.detector.detect(configs)
        
        # 验证：应该检测到敏感信息
        self.assertGreater(len(result), 0)
        
        # 验证：路径应只包含 key
        item = result[0]
        self.assertEqual(
            item['path'],
            key,
            f"顶层配置项的路径应只包含 key: {key}"
        )
    
    @given(
        section=section_name_strategy(),
        key=key_name_strategy(),
        digit_counts=st.lists(
            st.integers(min_value=5, max_value=11),
            min_size=2,
            max_size=5
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_27_multiple_matches_in_single_location(
        self,
        section,
        key,
        digit_counts
    ):
        """属性 27: 敏感信息位置记录（单个位置多个匹配）
        
        Feature: persona-card-upload, Property 27: 敏感信息位置记录
        **验证需求：8.4**
        
        对于单个配置项中的多个敏感数字，系统应在同一位置记录所有匹配。
        """
        # 生成多个敏感数字
        sensitive_numbers = []
        for count in digit_counts:
            number = ''.join([str(random.randint(0, 9)) for _ in range(count)])
            sensitive_numbers.append(number)
        
        # 构建包含多个敏感数字的值
        test_value = ' '.join(sensitive_numbers)
        
        # 构建配置项
        configs = [
            {
                'section': section,
                'key': key,
                'value': test_value
            }
        ]
        
        # 检测敏感信息
        result = self.detector.detect(configs)
        
        # 验证：应该只有一个检测结果（同一位置）
        self.assertEqual(
            len(result),
            1,
            f"应该只有一个检测结果（同一位置）"
        )
        
        # 验证：matches 字段应包含所有敏感数字
        item = result[0]
        for number in sensitive_numbers:
            self.assertIn(
                number,
                item['matches'],
                f"matches 字段应包含 {number}"
            )
        
        # 验证：路径应正确
        expected_path = f"{section}.{key}"
        self.assertEqual(
            item['path'],
            expected_path,
            f"路径应为 {expected_path}"
        )

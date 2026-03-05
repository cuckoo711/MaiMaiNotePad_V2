"""TOML 验证器属性测试模块

使用 Hypothesis 进行基于属性的测试，验证 TOML 文件往返一致性。

**Validates: Requirements 2.13, 9.1, 9.2, 9.3**
"""

import tempfile
import os
import tomllib
from hypothesis import given, settings, strategies as st, assume
from hypothesis.extra.django import TestCase

from mainotebook.content.services.toml_validator import TOMLValidator


# 配置 Hypothesis
settings.register_profile("default", max_examples=100, deadline=None)
settings.load_profile("default")


# TOML 值生成策略
def toml_string_strategy():
    """生成有效的 TOML 字符串值"""
    return st.text(
        alphabet=st.characters(
            whitelist_categories=('Ll', 'Lu', 'Nd', 'Zs'),
            blacklist_characters='\n\r\t\\"'
        ),
        min_size=1,
        max_size=50
    )


def toml_integer_strategy():
    """生成有效的 TOML 整数值"""
    return st.integers(min_value=-1000000, max_value=1000000)


def toml_float_strategy():
    """生成有效的 TOML 浮点数值"""
    return st.floats(
        min_value=-1000000.0,
        max_value=1000000.0,
        allow_nan=False,
        allow_infinity=False
    )


def toml_boolean_strategy():
    """生成有效的 TOML 布尔值"""
    return st.booleans()


def toml_array_strategy():
    """生成有效的 TOML 数组值（同类型元素）"""
    return st.one_of(
        st.lists(toml_string_strategy(), min_size=0, max_size=5),
        st.lists(toml_integer_strategy(), min_size=0, max_size=5),
        st.lists(toml_boolean_strategy(), min_size=0, max_size=5)
    )


def toml_value_strategy():
    """生成有效的 TOML 值（字符串、整数、浮点数、布尔值、数组）"""
    return st.one_of(
        toml_string_strategy(),
        toml_integer_strategy(),
        toml_float_strategy(),
        toml_boolean_strategy(),
        toml_array_strategy()
    )


def toml_key_strategy():
    """生成有效的 TOML 键名（仅 ASCII 字母和数字）"""
    return st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_',
        min_size=1,
        max_size=20
    ).filter(lambda x: x and x[0].isalpha())  # 键名必须以字母开头


def toml_section_strategy():
    """生成有效的 TOML 节名（仅 ASCII 字母和数字）"""
    return st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_',
        min_size=1,
        max_size=20
    ).filter(lambda x: x and x[0].isalpha())


class TOMLRoundTripConsistencyPropertyTest(TestCase):
    """TOML 文件往返一致性属性测试
    
    **属性 12：TOML 文件往返一致性**
    **Validates: Requirements 2.13, 9.1, 9.2, 9.3**
    
    验证 TOML 文件的往返一致性：
    - 解析有效的 TOML 文件后序列化，内容应等价
    - 必需字段（version）应被保留
    - TOML 语法应在往返后保持有效
    - 无效的 TOML 应被拒绝并提供清晰的错误消息
    """
    
    @given(
        version=toml_string_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_minimal_valid_toml_round_trip(self, version):
        """属性：包含 version 字段的最小 TOML 应通过往返测试
        
        **Validates: Requirements 2.13, 9.1, 9.2, 9.3**
        
        对于任意有效的 version 字符串值，
        创建包含该字段的 TOML 内容，
        解析后序列化应得到等价的内容。
        """
        # 跳过空字符串
        assume(version.strip())
        
        # 创建最小的有效 TOML 内容
        original_content = f'version = "{version}"'
        
        # 验证 TOML 内容
        is_valid, error_msg = TOMLValidator.validate_content(original_content)
        
        # 断言：包含 version 字段的 TOML 应该有效
        self.assertTrue(
            is_valid,
            f"有效的 TOML 验证失败: version={version}, 错误={error_msg}"
        )
        self.assertEqual(error_msg, "")
        
        # 解析 TOML
        parsed_data = tomllib.loads(original_content)
        
        # 断言：解析后应包含 version 字段
        self.assertIn('version', parsed_data)
        self.assertEqual(parsed_data['version'], version)
        
        # 序列化回 TOML（使用简单的格式）
        serialized_content = f'version = "{parsed_data["version"]}"'
        
        # 再次解析序列化后的内容
        reparsed_data = tomllib.loads(serialized_content)
        
        # 断言：往返后的数据应该等价
        self.assertEqual(
            reparsed_data,
            parsed_data,
            f"TOML 往返后数据不一致: 原始={parsed_data}, 往返={reparsed_data}"
        )
    
    @given(
        version=toml_string_strategy(),
        extra_fields=st.dictionaries(
            keys=toml_key_strategy(),
            values=toml_value_strategy(),
            min_size=0,
            max_size=5
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_toml_with_extra_fields_round_trip(self, version, extra_fields):
        """属性：包含额外字段的 TOML 应通过往返测试
        
        **Validates: Requirements 2.13, 9.1, 9.2**
        
        对于包含 version 字段和任意额外字段的 TOML，
        解析后序列化应得到等价的内容，
        所有字段都应被保留。
        """
        # 跳过空 version
        assume(version.strip())
        
        # 确保 version 不在额外字段中（避免冲突）
        assume('version' not in extra_fields)
        
        # 构建 TOML 内容
        toml_lines = [f'version = "{version}"']
        
        for key, value in extra_fields.items():
            if isinstance(value, str):
                toml_lines.append(f'{key} = "{value}"')
            elif isinstance(value, bool):
                toml_lines.append(f'{key} = {str(value).lower()}')
            elif isinstance(value, (int, float)):
                toml_lines.append(f'{key} = {value}')
            elif isinstance(value, list):
                # 简单数组序列化
                if all(isinstance(item, str) for item in value):
                    array_str = ', '.join(f'"{item}"' for item in value)
                elif all(isinstance(item, bool) for item in value):
                    array_str = ', '.join(str(item).lower() for item in value)
                elif all(isinstance(item, (int, float)) for item in value):
                    array_str = ', '.join(str(item) for item in value)
                else:
                    continue  # 跳过混合类型数组
                toml_lines.append(f'{key} = [{array_str}]')
        
        original_content = '\n'.join(toml_lines)
        
        # 验证 TOML 内容
        is_valid, error_msg = TOMLValidator.validate_content(original_content)
        
        # 断言：有效的 TOML 应该通过验证
        self.assertTrue(
            is_valid,
            f"有效的 TOML 验证失败: 错误={error_msg}\n内容:\n{original_content}"
        )
        
        # 解析 TOML
        parsed_data = tomllib.loads(original_content)
        
        # 断言：version 字段应被保留
        self.assertIn('version', parsed_data)
        self.assertEqual(parsed_data['version'], version)
        
        # 断言：所有额外字段应被保留
        for key in extra_fields.keys():
            self.assertIn(
                key,
                parsed_data,
                f"字段 {key} 在解析后丢失"
            )
        
        # 序列化回 TOML
        serialized_lines = []
        for key, value in parsed_data.items():
            if isinstance(value, str):
                serialized_lines.append(f'{key} = "{value}"')
            elif isinstance(value, bool):
                serialized_lines.append(f'{key} = {str(value).lower()}')
            elif isinstance(value, (int, float)):
                serialized_lines.append(f'{key} = {value}')
            elif isinstance(value, list):
                if all(isinstance(item, str) for item in value):
                    array_str = ', '.join(f'"{item}"' for item in value)
                elif all(isinstance(item, bool) for item in value):
                    array_str = ', '.join(str(item).lower() for item in value)
                elif all(isinstance(item, (int, float)) for item in value):
                    array_str = ', '.join(str(item) for item in value)
                else:
                    continue
                serialized_lines.append(f'{key} = [{array_str}]')
        
        serialized_content = '\n'.join(serialized_lines)
        
        # 再次解析序列化后的内容
        reparsed_data = tomllib.loads(serialized_content)
        
        # 断言：往返后的数据应该等价
        self.assertEqual(
            reparsed_data,
            parsed_data,
            f"TOML 往返后数据不一致"
        )
    
    @given(
        version=toml_string_strategy(),
        section_name=toml_section_strategy(),
        section_fields=st.dictionaries(
            keys=toml_key_strategy(),
            values=toml_value_strategy(),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_toml_with_sections_round_trip(self, version, section_name, section_fields):
        """属性：包含节（section）的 TOML 应通过往返测试
        
        **Validates: Requirements 9.1, 9.2**
        
        对于包含节的 TOML 文件，
        解析后序列化应得到等价的内容，
        节结构和字段都应被保留。
        """
        # 跳过空值
        assume(version.strip())
        assume(section_name.strip())
        
        # 构建 TOML 内容
        toml_lines = [f'version = "{version}"', '', f'[{section_name}]']
        
        for key, value in section_fields.items():
            if isinstance(value, str):
                toml_lines.append(f'{key} = "{value}"')
            elif isinstance(value, bool):
                toml_lines.append(f'{key} = {str(value).lower()}')
            elif isinstance(value, (int, float)):
                toml_lines.append(f'{key} = {value}')
            elif isinstance(value, list):
                if all(isinstance(item, str) for item in value):
                    array_str = ', '.join(f'"{item}"' for item in value)
                elif all(isinstance(item, bool) for item in value):
                    array_str = ', '.join(str(item).lower() for item in value)
                elif all(isinstance(item, (int, float)) for item in value):
                    array_str = ', '.join(str(item) for item in value)
                else:
                    continue
                toml_lines.append(f'{key} = [{array_str}]')
        
        original_content = '\n'.join(toml_lines)
        
        # 验证 TOML 内容
        is_valid, error_msg = TOMLValidator.validate_content(original_content)
        
        # 断言：有效的 TOML 应该通过验证
        self.assertTrue(
            is_valid,
            f"有效的 TOML 验证失败: 错误={error_msg}\n内容:\n{original_content}"
        )
        
        # 解析 TOML
        parsed_data = tomllib.loads(original_content)
        
        # 断言：version 字段应被保留
        self.assertIn('version', parsed_data)
        self.assertEqual(parsed_data['version'], version)
        
        # 断言：节应被保留
        self.assertIn(section_name, parsed_data)
        self.assertIsInstance(parsed_data[section_name], dict)
        
        # 断言：节中的字段应被保留
        for key in section_fields.keys():
            self.assertIn(
                key,
                parsed_data[section_name],
                f"节 {section_name} 中的字段 {key} 在解析后丢失"
            )
        
        # 序列化回 TOML
        serialized_lines = []
        
        # 先序列化顶层字段
        for key, value in parsed_data.items():
            if not isinstance(value, dict):
                if isinstance(value, str):
                    serialized_lines.append(f'{key} = "{value}"')
                elif isinstance(value, bool):
                    serialized_lines.append(f'{key} = {str(value).lower()}')
                elif isinstance(value, (int, float)):
                    serialized_lines.append(f'{key} = {value}')
        
        # 再序列化节
        for section_key, section_value in parsed_data.items():
            if isinstance(section_value, dict):
                serialized_lines.append('')
                serialized_lines.append(f'[{section_key}]')
                for key, value in section_value.items():
                    if isinstance(value, str):
                        serialized_lines.append(f'{key} = "{value}"')
                    elif isinstance(value, bool):
                        serialized_lines.append(f'{key} = {str(value).lower()}')
                    elif isinstance(value, (int, float)):
                        serialized_lines.append(f'{key} = {value}')
                    elif isinstance(value, list):
                        if all(isinstance(item, str) for item in value):
                            array_str = ', '.join(f'"{item}"' for item in value)
                        elif all(isinstance(item, bool) for item in value):
                            array_str = ', '.join(str(item).lower() for item in value)
                        elif all(isinstance(item, (int, float)) for item in value):
                            array_str = ', '.join(str(item) for item in value)
                        else:
                            continue
                        serialized_lines.append(f'{key} = [{array_str}]')
        
        serialized_content = '\n'.join(serialized_lines)
        
        # 再次解析序列化后的内容
        reparsed_data = tomllib.loads(serialized_content)
        
        # 断言：往返后的数据应该等价
        self.assertEqual(
            reparsed_data,
            parsed_data,
            f"TOML 往返后数据不一致"
        )
    
    def test_missing_version_field_fails_validation(self):
        """属性：缺少 version 字段的 TOML 应被拒绝
        
        **Validates: Requirements 2.13, 9.3**
        
        对于不包含 version 字段的 TOML 文件，
        验证应该失败，并提供明确的错误消息。
        """
        # 创建不包含 version 字段的 TOML
        invalid_content = 'name = "test"\ndescription = "test description"'
        
        # 验证 TOML 内容
        is_valid, error_msg = TOMLValidator.validate_content(invalid_content)
        
        # 断言：缺少 version 字段应被拒绝
        self.assertFalse(
            is_valid,
            "缺少 version 字段的 TOML 未被拒绝"
        )
        self.assertIn("version", error_msg.lower())
        self.assertIn("缺少", error_msg)
    
    @given(
        version_value=st.one_of(
            toml_integer_strategy(),
            toml_float_strategy(),
            toml_boolean_strategy(),
            st.lists(toml_string_strategy(), min_size=1, max_size=3)
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_non_string_version_field_fails_validation(self, version_value):
        """属性：version 字段类型错误的 TOML 应被拒绝
        
        **Validates: Requirements 2.13, 9.3**
        
        对于 version 字段不是字符串类型的 TOML 文件，
        验证应该失败，并提供明确的错误消息。
        """
        # 构建包含非字符串 version 的 TOML
        if isinstance(version_value, bool):
            invalid_content = f'version = {str(version_value).lower()}'
        elif isinstance(version_value, (int, float)):
            invalid_content = f'version = {version_value}'
        elif isinstance(version_value, list):
            # 只使用字符串数组（其他类型会导致 TOML 语法错误）
            array_str = ', '.join(f'"{item}"' for item in version_value)
            invalid_content = f'version = [{array_str}]'
        else:
            return
        
        # 验证 TOML 内容
        is_valid, error_msg = TOMLValidator.validate_content(invalid_content)
        
        # 断言：version 字段类型错误应被拒绝
        self.assertFalse(
            is_valid,
            f"version 字段类型错误的 TOML 未被拒绝: 类型={type(version_value).__name__}"
        )
        # 错误消息可能来自 TOML 解析器或我们的类型检查
        # 只要被拒绝即可，不强制要求特定的错误消息格式
        self.assertTrue(
            "version" in error_msg.lower() or "字符串" in error_msg or "语法错误" in error_msg,
            f"错误消息不够明确: {error_msg}"
        )
    
    @given(
        invalid_syntax=st.sampled_from([
            'version = "test',  # 缺少引号
            'version "test"',  # 缺少等号
            'version = test',  # 字符串缺少引号
            '[section\nkey = "value"',  # 节名缺少闭合括号
            'version = "test"\n[',  # 不完整的节声明
            'version = "test"\nkey = ',  # 缺少值
            'version = "test"\n= "value"',  # 缺少键
            'version = "test"\nkey key = "value"',  # 重复键名
        ])
    )
    @settings(max_examples=100, deadline=None)
    def test_invalid_toml_syntax_fails_validation(self, invalid_syntax):
        """属性：语法错误的 TOML 应被拒绝
        
        **Validates: Requirements 9.2**
        
        对于包含语法错误的 TOML 文件，
        验证应该失败，并提供明确的错误消息。
        """
        # 验证 TOML 内容
        is_valid, error_msg = TOMLValidator.validate_content(invalid_syntax)
        
        # 断言：语法错误的 TOML 应被拒绝
        self.assertFalse(
            is_valid,
            f"语法错误的 TOML 未被拒绝: {invalid_syntax}"
        )
        self.assertIn("语法错误", error_msg)
    
    @given(
        version=toml_string_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_toml_file_round_trip(self, version):
        """属性：通过文件路径验证的 TOML 应通过往返测试
        
        **Validates: Requirements 2.13, 9.1, 9.2, 9.3**
        
        对于保存到文件的有效 TOML，
        通过文件路径验证应该成功，
        并且文件内容应该可以正确解析。
        """
        # 跳过空 version
        assume(version.strip())
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False, encoding='utf-8') as f:
            toml_content = f'version = "{version}"'
            f.write(toml_content)
            temp_file_path = f.name
        
        try:
            # 验证文件
            is_valid, error_msg = TOMLValidator.validate_file(temp_file_path)
            
            # 断言：有效的 TOML 文件应通过验证
            self.assertTrue(
                is_valid,
                f"有效的 TOML 文件验证失败: version={version}, 错误={error_msg}"
            )
            self.assertEqual(error_msg, "")
            
            # 读取并解析文件
            with open(temp_file_path, 'rb') as f:
                parsed_data = tomllib.loads(f.read().decode('utf-8'))
            
            # 断言：解析后应包含 version 字段
            self.assertIn('version', parsed_data)
            self.assertEqual(parsed_data['version'], version)
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def test_nonexistent_file_fails_validation(self):
        """属性：不存在的文件应被拒绝
        
        **Validates: Requirements 9.1**
        
        对于不存在的文件路径，
        验证应该失败，并提供明确的错误消息。
        """
        # 使用不存在的文件路径
        nonexistent_path = '/tmp/nonexistent_file_12345.toml'
        
        # 验证文件
        is_valid, error_msg = TOMLValidator.validate_file(nonexistent_path)
        
        # 断言：不存在的文件应被拒绝
        self.assertFalse(
            is_valid,
            "不存在的文件未被拒绝"
        )
        self.assertIn("不存在", error_msg)
    
    @given(
        version=toml_string_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_toml_with_comments_preserves_data(self, version):
        """属性：包含注释的 TOML 应正确解析数据
        
        **Validates: Requirements 9.1, 9.2**
        
        对于包含注释的 TOML 文件，
        解析应该忽略注释，正确提取数据。
        注意：注释在序列化时会丢失，这是预期行为。
        """
        # 跳过空 version
        assume(version.strip())
        
        # 创建包含注释的 TOML
        toml_content = f'''# This is a comment
version = "{version}"  # Inline comment
# Another comment
'''
        
        # 验证 TOML 内容
        is_valid, error_msg = TOMLValidator.validate_content(toml_content)
        
        # 断言：包含注释的 TOML 应该有效
        self.assertTrue(
            is_valid,
            f"包含注释的 TOML 验证失败: 错误={error_msg}"
        )
        
        # 解析 TOML
        parsed_data = tomllib.loads(toml_content)
        
        # 断言：version 字段应被正确解析
        self.assertIn('version', parsed_data)
        self.assertEqual(parsed_data['version'], version)
    
    @given(
        version=toml_string_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_toml_with_whitespace_preserves_data(self, version):
        """属性：包含额外空白的 TOML 应正确解析数据
        
        **Validates: Requirements 9.1, 9.2**
        
        对于包含额外空白（空行、缩进）的 TOML 文件，
        解析应该忽略空白，正确提取数据。
        """
        # 跳过空 version
        assume(version.strip())
        
        # 创建包含额外空白的 TOML
        toml_content = f'''

    version = "{version}"
    
    
'''
        
        # 验证 TOML 内容
        is_valid, error_msg = TOMLValidator.validate_content(toml_content)
        
        # 断言：包含额外空白的 TOML 应该有效
        self.assertTrue(
            is_valid,
            f"包含额外空白的 TOML 验证失败: 错误={error_msg}"
        )
        
        # 解析 TOML
        parsed_data = tomllib.loads(toml_content)
        
        # 断言：version 字段应被正确解析
        self.assertIn('version', parsed_data)
        self.assertEqual(parsed_data['version'], version)

"""TOML 解析服务属性测试

使用 Hypothesis 进行基于属性的测试，验证 TOML 解析服务的正确性属性。

**验证需求：4.1, 4.2, 4.3, 4.4, 4.5**

属性列表：
- 属性 13: TOML 解析完整性
- 属性 14: 数据类型识别
- 属性 15: 注释提取
- 属性 16: 注释关联
- 属性 17: version 字段验证
"""

import tempfile
import os
import tomllib
from hypothesis import given, settings, strategies as st, assume
from hypothesis.extra.django import TestCase

from mainotebook.content.services.toml_parser_service import TomlParserService


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


class TomlParserPropertiesTest(TestCase):
    """TOML 解析服务属性测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时目录用于测试文件
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后清理"""
        # 清理临时文件
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _create_temp_toml_file(self, content: str) -> str:
        """辅助方法：创建临时 TOML 文件
        
        Args:
            content: TOML 文件内容
            
        Returns:
            str: 临时文件路径
        """
        file_path = os.path.join(self.temp_dir, 'test_config.toml')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path
    
    # ========== 属性 13: TOML 解析完整性 ==========
    
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
    def test_property_13_toml_parsing_completeness(self, version, extra_fields):
        """属性 13: TOML 解析完整性
        
        Feature: persona-card-upload, Property 13: TOML 解析完整性
        **验证需求：4.1**
        
        对于任意有效的 TOML 文件，解析器应提取所有配置块、键名、值和数据类型，
        不遗漏任何配置项。
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
        
        content = '\n'.join(toml_lines)
        
        # 解析 TOML
        result = TomlParserService.parse_content(content)
        
        # 验证：version 字段应被提取
        self.assertEqual(result['version'], version)
        
        # 验证：所有配置项应被提取
        self.assertIn('sections', result)
        sections = result['sections']
        self.assertGreater(len(sections), 0)
        
        # 查找顶层 section
        top_section = next((s for s in sections if s['name'] == ''), None)
        self.assertIsNotNone(top_section, "顶层 section 应该存在")
        
        # 验证：所有额外字段应被提取
        items = {item['key']: item for item in top_section['items']}
        
        # version 应该在配置项中
        self.assertIn('version', items, "version 字段应被提取")
        
        # 所有额外字段应该在配置项中
        for key in extra_fields.keys():
            self.assertIn(
                key,
                items,
                f"配置项 {key} 应被提取，但未找到"
            )
    
    # ========== 属性 14: 数据类型识别 ==========
    
    @given(
        version=toml_string_strategy(),
        string_value=toml_string_strategy(),
        int_value=toml_integer_strategy(),
        float_value=toml_float_strategy(),
        bool_value=toml_boolean_strategy(),
        array_value=toml_array_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_14_data_type_identification(
        self,
        version,
        string_value,
        int_value,
        float_value,
        bool_value,
        array_value
    ):
        """属性 14: 数据类型识别
        
        Feature: persona-card-upload, Property 14: 数据类型识别
        **验证需求：4.2**
        
        对于任意 TOML 配置项，解析器应正确识别其数据类型
        （string、integer、float、boolean、array、object）。
        """
        # 跳过空 version
        assume(version.strip())
        assume(string_value.strip())
        
        # 构建 TOML 内容
        toml_lines = [
            f'version = "{version}"',
            f'str_field = "{string_value}"',
            f'int_field = {int_value}',
            f'float_field = {float_value}',
            f'bool_field = {str(bool_value).lower()}'
        ]
        
        # 添加数组字段
        if isinstance(array_value, list) and len(array_value) > 0:
            if all(isinstance(item, str) for item in array_value):
                array_str = ', '.join(f'"{item}"' for item in array_value)
                toml_lines.append(f'array_field = [{array_str}]')
            elif all(isinstance(item, bool) for item in array_value):
                array_str = ', '.join(str(item).lower() for item in array_value)
                toml_lines.append(f'array_field = [{array_str}]')
            elif all(isinstance(item, (int, float)) for item in array_value):
                array_str = ', '.join(str(item) for item in array_value)
                toml_lines.append(f'array_field = [{array_str}]')
        
        content = '\n'.join(toml_lines)
        
        # 解析 TOML
        result = TomlParserService.parse_content(content)
        
        # 查找顶层 section
        top_section = next((s for s in result['sections'] if s['name'] == ''), None)
        self.assertIsNotNone(top_section)
        
        items = {item['key']: item for item in top_section['items']}
        
        # 验证：字符串类型应被正确识别
        self.assertEqual(
            items['version']['type'],
            'string',
            f"version 字段应识别为 string 类型"
        )
        self.assertEqual(
            items['str_field']['type'],
            'string',
            f"str_field 应识别为 string 类型"
        )
        
        # 验证：整数类型应被正确识别
        self.assertEqual(
            items['int_field']['type'],
            'integer',
            f"int_field 应识别为 integer 类型，值为 {int_value}"
        )
        
        # 验证：浮点数类型应被正确识别
        self.assertEqual(
            items['float_field']['type'],
            'float',
            f"float_field 应识别为 float 类型，值为 {float_value}"
        )
        
        # 验证：布尔类型应被正确识别
        self.assertEqual(
            items['bool_field']['type'],
            'boolean',
            f"bool_field 应识别为 boolean 类型，值为 {bool_value}"
        )
        
        # 验证：数组类型应被正确识别（如果存在）
        if 'array_field' in items:
            self.assertEqual(
                items['array_field']['type'],
                'array',
                f"array_field 应识别为 array 类型"
            )
    
    # ========== 属性 15: 注释提取 ==========
    
    @given(
        version=toml_string_strategy(),
        comment_text=st.text(
            alphabet=st.characters(
                whitelist_categories=('Ll', 'Lu', 'Nd', 'Zs'),
                blacklist_characters='\n\r\t'
            ),
            min_size=1,
            max_size=50
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_15_comment_extraction(self, version, comment_text):
        """属性 15: 注释提取
        
        Feature: persona-card-upload, Property 15: 注释提取
        **验证需求：4.3**
        
        对于任意包含注释的 TOML 文件，解析器应提取所有以 # 开头的注释行。
        """
        # 跳过空值
        assume(version.strip())
        assume(comment_text.strip())
        
        # 构建包含注释的 TOML 内容
        content = f'''# {comment_text}
version = "{version}"
'''
        
        # 提取注释
        comments = TomlParserService.extract_comments(content)
        
        # 验证：注释应被提取
        self.assertGreater(
            len(comments),
            0,
            "应该提取到至少一个注释"
        )
        
        # 验证：注释内容应该包含原始文本
        found_comment = False
        for line_num, comment in comments.items():
            if comment_text.strip() in comment:
                found_comment = True
                break
        
        self.assertTrue(
            found_comment,
            f"应该找到包含 '{comment_text}' 的注释"
        )
    
    # ========== 属性 16: 注释关联 ==========
    
    @given(
        version=toml_string_strategy(),
        key_name=toml_key_strategy(),
        key_value=toml_string_strategy(),
        comment_text=st.text(
            alphabet=st.characters(
                whitelist_categories=('Ll', 'Lu', 'Nd', 'Zs'),
                blacklist_characters='\n\r\t'
            ),
            min_size=1,
            max_size=50
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_16_comment_association(
        self,
        version,
        key_name,
        key_value,
        comment_text
    ):
        """属性 16: 注释关联
        
        Feature: persona-card-upload, Property 16: 注释关联
        **验证需求：4.4**
        
        对于任意 TOML 文件中的注释，解析器应将其关联到紧随其后的配置块或配置项。
        """
        # 跳过空值和保留字
        assume(version.strip())
        assume(key_name.strip())
        assume(key_value.strip())
        assume(comment_text.strip())
        assume(key_name != 'version')  # 避免与 version 冲突
        
        # 构建包含注释的 TOML 内容
        content = f'''version = "{version}"
# {comment_text}
{key_name} = "{key_value}"
'''
        
        # 解析 TOML
        result = TomlParserService.parse_content(content)
        
        # 查找顶层 section
        top_section = next((s for s in result['sections'] if s['name'] == ''), None)
        self.assertIsNotNone(top_section)
        
        # 查找配置项
        target_item = next(
            (item for item in top_section['items'] if item['key'] == key_name),
            None
        )
        
        self.assertIsNotNone(
            target_item,
            f"应该找到配置项 {key_name}"
        )
        
        # 验证：注释应该关联到配置项
        self.assertIn(
            'comment',
            target_item,
            "配置项应该有 comment 字段"
        )
        
        # 验证：注释内容应该包含原始文本
        if target_item['comment']:
            self.assertIn(
                comment_text.strip(),
                target_item['comment'],
                f"配置项 {key_name} 的注释应包含 '{comment_text}'"
            )
    
    # ========== 属性 17: version 字段验证 ==========
    
    @given(
        fields=st.dictionaries(
            keys=toml_key_strategy(),
            values=toml_value_strategy(),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_17_version_field_validation(self, fields):
        """属性 17: version 字段验证
        
        Feature: persona-card-upload, Property 17: version 字段验证
        **验证需求：4.5**
        
        对于任意 TOML 文件，解析器应验证其包含 version 字段
        （在顶层或 inner.meta.card 中），缺少该字段的文件应被拒绝。
        """
        # 确保 fields 中没有 version 字段
        assume('version' not in fields)
        
        # 构建不包含 version 的 TOML 内容
        toml_lines = []
        
        for key, value in fields.items():
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
        
        content = '\n'.join(toml_lines)
        
        # 验证：缺少 version 字段应抛出 ValueError
        with self.assertRaises(ValueError) as context:
            TomlParserService.parse_content(content)
        
        # 验证：错误消息应提到 version
        self.assertIn(
            'version',
            str(context.exception).lower(),
            "错误消息应提到缺少 version 字段"
        )
    
    @given(
        version=toml_string_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_17_version_field_validation_with_version(self, version):
        """属性 17: version 字段验证（包含 version 的情况）
        
        Feature: persona-card-upload, Property 17: version 字段验证
        **验证需求：4.5**
        
        对于包含 version 字段的 TOML 文件，解析器应成功验证。
        """
        # 跳过空 version
        assume(version.strip())
        
        # 构建包含 version 的 TOML 内容
        content = f'version = "{version}"'
        
        # 验证：包含 version 字段应成功解析
        result = TomlParserService.parse_content(content)
        
        # 验证：version 字段应被正确提取
        self.assertEqual(
            result['version'],
            version,
            f"version 字段应为 {version}"
        )
    
    @given(
        version=toml_string_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_17_version_field_validation_nested(self, version):
        """属性 17: version 字段验证（嵌套 version 的情况）
        
        Feature: persona-card-upload, Property 17: version 字段验证
        **验证需求：4.5**
        
        对于 version 在 inner.meta.card 中的 TOML 文件，解析器应成功验证。
        """
        # 跳过空 version
        assume(version.strip())
        
        # 构建包含嵌套 version 的 TOML 内容
        content = f'''[inner.meta.card]
version = "{version}"
'''
        
        # 验证：包含嵌套 version 字段应成功解析
        result = TomlParserService.parse_content(content)
        
        # 验证：version 字段应被正确提取
        self.assertEqual(
            result['version'],
            version,
            f"嵌套的 version 字段应为 {version}"
        )

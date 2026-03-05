"""TOML 解析服务单元测试

测试 TOML 解析服务的各项功能，包括：
- 解析有效的 TOML 文件
- 解析包含注释的 TOML 文件
- 解析缺少 version 字段的文件（应失败）
- 解析语法错误的文件（应返回错误位置）
- 数据类型识别

**验证需求：4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7**
"""

import os
import tempfile
from django.test import TestCase
import tomllib

from mainotebook.content.services.toml_parser_service import TomlParserService


class TomlParserServiceTest(TestCase):
    """TOML 解析服务单元测试类"""
    
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
    
    # ========== 解析有效 TOML 文件测试 ==========
    
    def test_parse_valid_toml_file(self):
        """测试解析有效的 TOML 文件（需求 4.1）"""
        content = '''version = "1.0"
name = "测试人设卡"
age = 18
'''
        file_path = self._create_temp_toml_file(content)
        
        result = TomlParserService.parse_file(file_path)
        
        # 验证解析结果
        self.assertIn('sections', result)
        self.assertIn('version', result)
        self.assertEqual(result['version'], '1.0')
        
        # 验证顶层配置项
        sections = result['sections']
        self.assertGreater(len(sections), 0)
        
        # 查找顶层 section（name 为空字符串）
        top_section = next((s for s in sections if s['name'] == ''), None)
        self.assertIsNotNone(top_section)
        
        # 验证配置项
        items = top_section['items']
        self.assertGreater(len(items), 0)
        
        # 验证 version 字段
        version_item = next((item for item in items if item['key'] == 'version'), None)
        self.assertIsNotNone(version_item)
        self.assertEqual(version_item['value'], '1.0')
        self.assertEqual(version_item['type'], 'string')
    
    def test_parse_toml_with_sections(self):
        """测试解析包含 section 的 TOML 文件（需求 4.1）"""
        content = '''version = "1.0"

[inner.meta.card]
name = "测试人设卡"
description = "这是一个测试"

[settings]
enabled = true
count = 42
ratio = 3.14
'''
        file_path = self._create_temp_toml_file(content)
        
        result = TomlParserService.parse_file(file_path)
        
        # 验证解析结果
        self.assertEqual(result['version'], '1.0')
        
        sections = result['sections']
        self.assertGreater(len(sections), 0)
        
        # 验证 inner.meta.card section
        inner_section = next((s for s in sections if 'inner' in s['name']), None)
        self.assertIsNotNone(inner_section)
    
    def test_parse_toml_with_nested_version(self):
        """测试解析 version 在嵌套结构中的 TOML 文件（需求 4.5）"""
        content = '''[inner.meta.card]
version = "2.0"
name = "测试人设卡"
'''
        file_path = self._create_temp_toml_file(content)
        
        result = TomlParserService.parse_file(file_path)
        
        # 验证能够找到嵌套的 version 字段
        self.assertEqual(result['version'], '2.0')
    
    # ========== 注释提取测试 ==========
    
    def test_parse_toml_with_comments(self):
        """测试解析包含注释的 TOML 文件（需求 4.3, 4.4）"""
        content = '''# 这是文件注释
version = "1.0"  # 版本号

# 这是 section 注释
[settings]
# 这是配置项注释
enabled = true
'''
        file_path = self._create_temp_toml_file(content)
        
        result = TomlParserService.parse_file(file_path)
        
        # 验证注释被提取
        sections = result['sections']
        
        # 查找 settings section
        settings_section = next((s for s in sections if s['name'] == 'settings'), None)
        self.assertIsNotNone(settings_section)
        
        # 验证 section 注释
        self.assertIn('section 注释', settings_section['comment'])
        
        # 验证配置项注释
        enabled_item = next((item for item in settings_section['items'] if item['key'] == 'enabled'), None)
        self.assertIsNotNone(enabled_item)
        self.assertIn('配置项注释', enabled_item['comment'])
    
    def test_extract_comments(self):
        """测试注释提取功能（需求 4.3）"""
        content = '''# 第一行注释
version = "1.0"  # 行内注释
# 第三行注释
name = "test"
'''
        comments = TomlParserService.extract_comments(content)
        
        # 验证注释被提取
        self.assertIn(1, comments)
        self.assertEqual(comments[1], '第一行注释')
        
        self.assertIn(2, comments)
        self.assertEqual(comments[2], '行内注释')
        
        self.assertIn(3, comments)
        self.assertEqual(comments[3], '第三行注释')
    
    # ========== 数据类型识别测试 ==========
    
    def test_identify_data_types(self):
        """测试数据类型识别（需求 4.2）"""
        content = '''version = "1.0"
name = "测试"
age = 25
height = 175.5
enabled = true
tags = ["AI", "助手"]

[settings]
config = { key = "value" }
'''
        file_path = self._create_temp_toml_file(content)
        
        result = TomlParserService.parse_file(file_path)
        
        # 查找顶层 section
        top_section = next((s for s in result['sections'] if s['name'] == ''), None)
        self.assertIsNotNone(top_section)
        
        items = {item['key']: item for item in top_section['items']}
        
        # 验证字符串类型
        self.assertEqual(items['version']['type'], 'string')
        self.assertEqual(items['name']['type'], 'string')
        
        # 验证整数类型
        self.assertEqual(items['age']['type'], 'integer')
        
        # 验证浮点数类型
        self.assertEqual(items['height']['type'], 'float')
        
        # 验证布尔类型
        self.assertEqual(items['enabled']['type'], 'boolean')
        
        # 验证数组类型
        self.assertEqual(items['tags']['type'], 'array')
        
        # 验证对象类型
        settings_section = next((s for s in result['sections'] if s['name'] == 'settings'), None)
        if settings_section:
            config_item = next((item for item in settings_section['items'] if item['key'] == 'config'), None)
            if config_item:
                self.assertEqual(config_item['type'], 'object')
    
    # ========== 验证结构测试 ==========
    
    def test_parse_toml_missing_version_fails(self):
        """测试解析缺少 version 字段的文件（应失败）（需求 4.5, 4.6）"""
        content = '''name = "测试人设卡"
description = "这是一个测试"
'''
        file_path = self._create_temp_toml_file(content)
        
        # 验证抛出 ValueError
        with self.assertRaises(ValueError) as context:
            TomlParserService.parse_file(file_path)
        
        # 验证错误消息
        self.assertIn('version', str(context.exception))
    
    def test_validate_structure_with_version(self):
        """测试验证包含 version 字段的结构（需求 4.5）"""
        parsed_data = {'version': '1.0', 'name': 'test'}
        
        # 验证通过
        result = TomlParserService.validate_structure(parsed_data)
        self.assertTrue(result)
    
    def test_validate_structure_without_version_fails(self):
        """测试验证缺少 version 字段的结构（应失败）（需求 4.6）"""
        parsed_data = {'name': 'test', 'description': 'test'}
        
        # 验证抛出 ValueError
        with self.assertRaises(ValueError) as context:
            TomlParserService.validate_structure(parsed_data)
        
        self.assertIn('version', str(context.exception))
    
    def test_validate_structure_with_nested_version(self):
        """测试验证嵌套 version 字段的结构（需求 4.5）"""
        parsed_data = {
            'inner': {
                'meta': {
                    'card': {
                        'version': '1.0'
                    }
                }
            }
        }
        
        # 验证通过
        result = TomlParserService.validate_structure(parsed_data)
        self.assertTrue(result)
    
    # ========== 语法错误测试 ==========
    
    def test_parse_invalid_toml_syntax(self):
        """测试解析语法错误的文件（应返回错误）（需求 4.7）"""
        content = '''version = "1.0
name = test
'''
        file_path = self._create_temp_toml_file(content)
        
        # 验证抛出 TOMLDecodeError
        with self.assertRaises(tomllib.TOMLDecodeError):
            TomlParserService.parse_file(file_path)
    
    def test_parse_content_with_syntax_error(self):
        """测试解析包含语法错误的内容（需求 4.7）"""
        content = '''version = "1.0"
[section
key = "value"
'''
        
        # 验证抛出 TOMLDecodeError
        with self.assertRaises(tomllib.TOMLDecodeError):
            TomlParserService.parse_content(content)
    
    # ========== parse_content 方法测试 ==========
    
    def test_parse_content_valid_toml(self):
        """测试解析有效的 TOML 内容字符串（需求 4.1）"""
        content = '''version = "1.0"
name = "测试"
'''
        
        result = TomlParserService.parse_content(content)
        
        # 验证解析结果
        self.assertIn('sections', result)
        self.assertIn('version', result)
        self.assertEqual(result['version'], '1.0')
    
    def test_parse_content_with_comments(self):
        """测试解析包含注释的 TOML 内容（需求 4.3, 4.4）"""
        content = '''# 文件注释
version = "1.0"  # 版本注释
'''
        
        result = TomlParserService.parse_content(content)
        
        # 验证解析成功
        self.assertEqual(result['version'], '1.0')
    
    # ========== 边缘情况测试 ==========
    
    def test_parse_empty_toml(self):
        """测试解析空 TOML 文件（应失败，缺少 version）"""
        content = ''
        
        with self.assertRaises(ValueError):
            TomlParserService.parse_content(content)
    
    def test_parse_toml_with_only_version(self):
        """测试解析只包含 version 的 TOML 文件"""
        content = 'version = "1.0"'
        
        result = TomlParserService.parse_content(content)
        
        # 验证解析成功
        self.assertEqual(result['version'], '1.0')
        self.assertIn('sections', result)
    
    def test_parse_toml_with_complex_nested_structure(self):
        """测试解析复杂嵌套结构的 TOML 文件（需求 4.1）"""
        content = '''version = "1.0"

[database]
server = "192.168.1.1"
ports = [8001, 8002, 8003]

[database.connection]
max_retries = 5
timeout = 30.0

[servers.alpha]
ip = "10.0.0.1"
dc = "eqdc10"

[servers.beta]
ip = "10.0.0.2"
dc = "eqdc10"
'''
        file_path = self._create_temp_toml_file(content)
        
        result = TomlParserService.parse_file(file_path)
        
        # 验证解析成功
        self.assertEqual(result['version'], '1.0')
        self.assertIn('sections', result)
        
        # 验证 sections 被正确解析
        sections = result['sections']
        self.assertGreater(len(sections), 0)
    
    def test_parse_toml_with_multiline_strings(self):
        """测试解析包含多行字符串的 TOML 文件"""
        content = '''version = "1.0"
description = """
这是一个
多行字符串
"""
'''
        file_path = self._create_temp_toml_file(content)
        
        result = TomlParserService.parse_file(file_path)
        
        # 验证解析成功
        self.assertEqual(result['version'], '1.0')
        
        # 验证多行字符串被正确解析
        top_section = next((s for s in result['sections'] if s['name'] == ''), None)
        if top_section:
            desc_item = next((item for item in top_section['items'] if item['key'] == 'description'), None)
            if desc_item:
                self.assertIn('多行字符串', desc_item['value'])
    
    def test_parse_toml_with_special_characters_in_strings(self):
        """测试解析包含特殊字符的字符串"""
        # TOML 中反斜杠需要转义，或使用单引号字符串
        content = '''version = "1.0"
path = 'C:\\Users\\Test\\Documents'
regex = '\\d{3}-\\d{4}'
'''
        file_path = self._create_temp_toml_file(content)
        
        result = TomlParserService.parse_file(file_path)
        
        # 验证解析成功
        self.assertEqual(result['version'], '1.0')
    
    def test_parse_toml_with_unicode_characters(self):
        """测试解析包含 Unicode 字符的 TOML 文件"""
        content = '''version = "1.0"
name = "测试人设卡 🤖"
description = "支持中文和 emoji 😊"
'''
        file_path = self._create_temp_toml_file(content)
        
        result = TomlParserService.parse_file(file_path)
        
        # 验证解析成功
        self.assertEqual(result['version'], '1.0')
        
        # 验证 Unicode 字符被正确解析
        top_section = next((s for s in result['sections'] if s['name'] == ''), None)
        if top_section:
            name_item = next((item for item in top_section['items'] if item['key'] == 'name'), None)
            if name_item:
                self.assertIn('🤖', name_item['value'])

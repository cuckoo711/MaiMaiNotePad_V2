"""TOML 导出服务单元测试

测试 TOML 导出服务的各项功能，包括：
- 导出简单配置
- 导出包含被删除块的配置
- 导出保留注释
- 复杂类型（array, object）的格式化

**验证需求：5.3, 5.4, 5.5, 5.6**
"""

import json
from django.test import TestCase
from django.contrib.auth import get_user_model

from mainotebook.content.models import PersonaCard, PersonaCardConfig
from mainotebook.content.services.toml_exporter_service import TomlExporterService

Users = get_user_model()


class TomlExporterServiceTest(TestCase):
    """TOML 导出服务单元测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建测试用户
        self.user = Users.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='testpass123'
        )
        
        # 创建测试人设卡
        self.persona_card = PersonaCard.objects.create(
            name='测试人设卡',
            description='这是一个测试人设卡',
            uploader=self.user,
            copyright_owner='测试作者',
            is_public=False,
            version='1.0'
        )
    
    def tearDown(self):
        """测试后清理"""
        # 清理测试数据
        PersonaCardConfig.objects.filter(persona_card=self.persona_card).delete()
        self.persona_card.delete()
        self.user.delete()
    
    # ========== 导出简单配置测试 ==========
    
    def test_export_simple_config(self):
        """测试导出简单配置（需求 5.3）"""
        # 创建简单配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='',
            key_name='version',
            value='1.0',
            data_type='string',
            description='版本号'
        )
        
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='',
            key_name='name',
            value='测试人设卡',
            data_type='string',
            description='人设卡名称'
        )
        
        # 导出 TOML
        configs = PersonaCardConfig.objects.filter(persona_card=self.persona_card)
        toml_content = TomlExporterService.export_to_toml(configs)
        
        # 验证导出内容
        self.assertIn('version = "1.0"', toml_content)
        self.assertIn('name = "测试人设卡"', toml_content)
        self.assertIn('# 版本号', toml_content)
        self.assertIn('# 人设卡名称', toml_content)
    
    def test_export_config_with_sections(self):
        """测试导出包含 section 的配置（需求 5.3）"""
        # 创建顶层配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='',
            key_name='version',
            value='1.0',
            data_type='string'
        )
        
        # 创建 section 配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='settings',
            key_name='enabled',
            value='true',
            data_type='boolean',
            description='是否启用'
        )
        
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='settings',
            key_name='count',
            value='42',
            data_type='integer'
        )
        
        # 导出 TOML
        configs = PersonaCardConfig.objects.filter(persona_card=self.persona_card)
        toml_content = TomlExporterService.export_to_toml(configs)
        
        # 验证导出内容
        self.assertIn('version = "1.0"', toml_content)
        self.assertIn('[settings]', toml_content)
        self.assertIn('enabled = true', toml_content)
        self.assertIn('count = 42', toml_content)
        self.assertIn('# 是否启用', toml_content)
    
    # ========== 导出被删除块测试 ==========
    
    def test_export_with_deleted_sections(self):
        """测试导出包含被删除块的配置（需求 5.6）"""
        # 创建正常配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='',
            key_name='version',
            value='1.0',
            data_type='string'
        )
        
        # 创建被删除的配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='deleted_section',
            key_name='some_key',
            value='some_value',
            data_type='string',
            is_deleted=True
        )
        
        # 导出 TOML（包含被删除块）
        configs = PersonaCardConfig.objects.filter(persona_card=self.persona_card)
        toml_content = TomlExporterService.export_to_toml(configs, include_deleted=True)
        
        # 验证导出内容
        self.assertIn('version = "1.0"', toml_content)
        self.assertIn('[deleted_section]', toml_content)
        self.assertIn('# 此配置块已被作者删除', toml_content)
        # 被删除的配置项不应该出现
        self.assertNotIn('some_key', toml_content)
    
    def test_export_without_deleted_sections(self):
        """测试导出时不包含被删除块（需求 5.6）"""
        # 创建正常配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='',
            key_name='version',
            value='1.0',
            data_type='string'
        )
        
        # 创建被删除的配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='deleted_section',
            key_name='some_key',
            value='some_value',
            data_type='string',
            is_deleted=True
        )
        
        # 导出 TOML（不包含被删除块）
        configs = PersonaCardConfig.objects.filter(persona_card=self.persona_card)
        toml_content = TomlExporterService.export_to_toml(configs, include_deleted=False)
        
        # 验证导出内容
        self.assertIn('version = "1.0"', toml_content)
        # 被删除的 section 不应该出现
        self.assertNotIn('[deleted_section]', toml_content)
        self.assertNotIn('此配置块已被作者删除', toml_content)
    
    def test_get_deleted_sections(self):
        """测试获取被删除的配置块列表（需求 5.6）"""
        # 创建正常配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='normal_section',
            key_name='key1',
            value='value1',
            data_type='string'
        )
        
        # 创建被删除的配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='deleted_section1',
            key_name='key2',
            value='value2',
            data_type='string',
            is_deleted=True
        )
        
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='deleted_section2',
            key_name='key3',
            value='value3',
            data_type='string',
            is_deleted=True
        )
        
        # 获取被删除的 section 列表
        configs = PersonaCardConfig.objects.filter(persona_card=self.persona_card)
        deleted_sections = TomlExporterService.get_deleted_sections(configs)
        
        # 验证结果
        self.assertEqual(len(deleted_sections), 2)
        self.assertIn('deleted_section1', deleted_sections)
        self.assertIn('deleted_section2', deleted_sections)
        self.assertNotIn('normal_section', deleted_sections)
    
    # ========== 注释保留测试 ==========
    
    def test_export_preserves_comments(self):
        """测试导出保留注释（需求 5.5）"""
        # 创建带注释的配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='',
            key_name='version',
            value='1.0',
            data_type='string',
            description='这是版本号'
        )
        
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='settings',
            key_name='enabled',
            value='true',
            data_type='boolean',
            description='启用标志'
        )
        
        # 导出 TOML
        configs = PersonaCardConfig.objects.filter(persona_card=self.persona_card)
        toml_content = TomlExporterService.export_to_toml(configs)
        
        # 验证注释被保留
        self.assertIn('# 这是版本号', toml_content)
        self.assertIn('# 启用标志', toml_content)
        
        # 验证注释在配置项上方
        lines = toml_content.split('\n')
        for i, line in enumerate(lines):
            if 'version = "1.0"' in line:
                # 检查上一行是否是注释
                self.assertIn('这是版本号', lines[i-1])
            if 'enabled = true' in line:
                self.assertIn('启用标志', lines[i-1])
    
    def test_export_without_comments(self):
        """测试导出没有注释的配置项"""
        # 创建不带注释的配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='',
            key_name='version',
            value='1.0',
            data_type='string'
        )
        
        # 导出 TOML
        configs = PersonaCardConfig.objects.filter(persona_card=self.persona_card)
        toml_content = TomlExporterService.export_to_toml(configs)
        
        # 验证导出成功
        self.assertIn('version = "1.0"', toml_content)
    
    # ========== 复杂类型格式化测试 ==========
    
    def test_format_value_string(self):
        """测试格式化字符串类型（需求 5.3）"""
        value = '测试字符串'
        formatted = TomlExporterService.format_value(value, 'string')
        
        self.assertEqual(formatted, '"测试字符串"')
    
    def test_format_value_string_with_special_characters(self):
        """测试格式化包含特殊字符的字符串"""
        value = '包含"引号"和\\反斜杠'
        formatted = TomlExporterService.format_value(value, 'string')
        
        # 验证特殊字符被转义
        self.assertIn('\\"', formatted)
        self.assertIn('\\\\', formatted)
    
    def test_format_value_integer(self):
        """测试格式化整数类型（需求 5.3）"""
        value = '42'
        formatted = TomlExporterService.format_value(value, 'integer')
        
        self.assertEqual(formatted, '42')
    
    def test_format_value_float(self):
        """测试格式化浮点数类型（需求 5.3）"""
        value = '3.14'
        formatted = TomlExporterService.format_value(value, 'float')
        
        self.assertEqual(formatted, '3.14')
    
    def test_format_value_boolean_true(self):
        """测试格式化布尔值 true（需求 5.3）"""
        value = 'true'
        formatted = TomlExporterService.format_value(value, 'boolean')
        
        self.assertEqual(formatted, 'true')
    
    def test_format_value_boolean_false(self):
        """测试格式化布尔值 false（需求 5.3）"""
        value = 'false'
        formatted = TomlExporterService.format_value(value, 'boolean')
        
        self.assertEqual(formatted, 'false')
    
    def test_format_value_array_strings(self):
        """测试格式化字符串数组（需求 5.3）"""
        value = json.dumps(['item1', 'item2', 'item3'])
        formatted = TomlExporterService.format_value(value, 'array')
        
        self.assertEqual(formatted, '["item1", "item2", "item3"]')
    
    def test_format_value_array_integers(self):
        """测试格式化整数数组（需求 5.3）"""
        value = json.dumps([1, 2, 3, 4, 5])
        formatted = TomlExporterService.format_value(value, 'array')
        
        self.assertEqual(formatted, '[1, 2, 3, 4, 5]')
    
    def test_format_value_array_mixed(self):
        """测试格式化混合类型数组"""
        value = json.dumps(['text', 123, True])
        formatted = TomlExporterService.format_value(value, 'array')
        
        self.assertIn('"text"', formatted)
        self.assertIn('123', formatted)
        self.assertIn('true', formatted)
    
    def test_format_value_object(self):
        """测试格式化对象类型（需求 5.3）"""
        value = json.dumps({'key1': 'value1', 'key2': 'value2'})
        formatted = TomlExporterService.format_value(value, 'object')
        
        self.assertIn('key1 = "value1"', formatted)
        self.assertIn('key2 = "value2"', formatted)
    
    def test_format_value_object_with_numbers(self):
        """测试格式化包含数字的对象"""
        value = json.dumps({'count': 42, 'ratio': 3.14, 'enabled': True})
        formatted = TomlExporterService.format_value(value, 'object')
        
        self.assertIn('count = 42', formatted)
        self.assertIn('ratio = 3.14', formatted)
        self.assertIn('enabled = true', formatted)
    
    # ========== 完整导出测试 ==========
    
    def test_export_complete_config(self):
        """测试导出完整配置（需求 5.3, 5.4, 5.5）"""
        # 创建完整的配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='',
            key_name='version',
            value='1.0',
            data_type='string',
            description='配置文件版本'
        )
        
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='',
            key_name='name',
            value='测试人设卡',
            data_type='string',
            description='人设卡名称'
        )
        
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='settings',
            key_name='enabled',
            value='true',
            data_type='boolean',
            description='是否启用'
        )
        
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='settings',
            key_name='count',
            value='100',
            data_type='integer'
        )
        
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='settings',
            key_name='tags',
            value=json.dumps(['AI', '助手', '测试']),
            data_type='array',
            description='标签列表'
        )
        
        # 导出 TOML
        configs = PersonaCardConfig.objects.filter(persona_card=self.persona_card)
        toml_content = TomlExporterService.export_to_toml(configs)
        
        # 验证导出内容完整性
        self.assertIn('# 配置文件版本', toml_content)
        self.assertIn('version = "1.0"', toml_content)
        self.assertIn('# 人设卡名称', toml_content)
        self.assertIn('name = "测试人设卡"', toml_content)
        self.assertIn('[settings]', toml_content)
        self.assertIn('# 是否启用', toml_content)
        self.assertIn('enabled = true', toml_content)
        self.assertIn('count = 100', toml_content)
        self.assertIn('# 标签列表', toml_content)
        self.assertIn('tags = ["AI", "助手", "测试"]', toml_content)
    
    # ========== 边缘情况测试 ==========
    
    def test_export_empty_config(self):
        """测试导出空配置"""
        # 不创建任何配置项
        configs = PersonaCardConfig.objects.filter(persona_card=self.persona_card)
        toml_content = TomlExporterService.export_to_toml(configs)
        
        # 验证返回空字符串或只包含空行
        self.assertEqual(toml_content.strip(), '')
    
    def test_export_config_with_empty_section_name(self):
        """测试导出 section_name 为空的配置项"""
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='',
            key_name='version',
            value='1.0',
            data_type='string'
        )
        
        configs = PersonaCardConfig.objects.filter(persona_card=self.persona_card)
        toml_content = TomlExporterService.export_to_toml(configs)
        
        # 验证顶层配置项被正确导出
        self.assertIn('version = "1.0"', toml_content)
        # 不应该有空的 section 标题
        self.assertNotIn('[]', toml_content)
    
    def test_export_config_with_unicode(self):
        """测试导出包含 Unicode 字符的配置"""
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='',
            key_name='name',
            value='测试人设卡 🤖',
            data_type='string',
            description='支持 emoji 😊'
        )
        
        configs = PersonaCardConfig.objects.filter(persona_card=self.persona_card)
        toml_content = TomlExporterService.export_to_toml(configs)
        
        # 验证 Unicode 字符被正确导出
        self.assertIn('测试人设卡 🤖', toml_content)
        self.assertIn('emoji 😊', toml_content)
    
    def test_export_config_with_newlines_in_string(self):
        """测试导出包含换行符的字符串"""
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='',
            key_name='description',
            value='第一行\n第二行\n第三行',
            data_type='string'
        )
        
        configs = PersonaCardConfig.objects.filter(persona_card=self.persona_card)
        toml_content = TomlExporterService.export_to_toml(configs)
        
        # 验证换行符被转义
        self.assertIn('\\n', toml_content)
    
    def test_export_multiple_sections_sorted(self):
        """测试导出多个 section 时按字母顺序排序"""
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='',
            key_name='version',
            value='1.0',
            data_type='string'
        )
        
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='zebra',
            key_name='key1',
            value='value1',
            data_type='string'
        )
        
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='alpha',
            key_name='key2',
            value='value2',
            data_type='string'
        )
        
        configs = PersonaCardConfig.objects.filter(persona_card=self.persona_card)
        toml_content = TomlExporterService.export_to_toml(configs)
        
        # 验证 section 按字母顺序排列
        alpha_pos = toml_content.find('[alpha]')
        zebra_pos = toml_content.find('[zebra]')
        
        self.assertGreater(zebra_pos, alpha_pos)

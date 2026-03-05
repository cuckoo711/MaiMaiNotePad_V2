"""TOML 导出服务属性测试

使用 Hypothesis 进行基于属性的测试，验证 TOML 导出服务的正确性属性。

**验证需求：5.3, 5.4, 5.5, 5.6**

属性列表：
- 属性 18: TOML 导出有效性
- 属性 19: 往返属性（解析-导出-解析）
- 属性 20: 注释保留
- 属性 21: 被删除块处理
"""

import json
import tomllib
from hypothesis import given, settings, strategies as st, assume
from hypothesis.extra.django import TestCase
from django.contrib.auth import get_user_model

from mainotebook.content.models import PersonaCard, PersonaCardConfig
from mainotebook.content.services.toml_exporter_service import TomlExporterService
from mainotebook.content.services.toml_parser_service import TomlParserService

Users = get_user_model()


# 配置 Hypothesis
settings.register_profile("default", max_examples=100, deadline=None)
settings.load_profile("default")


# TOML 值生成策略（复用解析器的策略）
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


def deduplicate_configs(configs):
    """去重配置项并避免键名和 section 名冲突
    
    Args:
        configs: 配置项列表
        
    Returns:
        list: 去重后的配置项列表
    """
    seen = set()
    unique_configs = []
    top_level_keys = set()
    section_names = set()
    
    for config in configs:
        key = (config['section_name'], config['key_name'])
        if key not in seen:
            # 检查是否会导致冲突
            if config['section_name'] == '':
                # 顶层键
                if config['key_name'] not in section_names:
                    seen.add(key)
                    top_level_keys.add(config['key_name'])
                    unique_configs.append(config)
            else:
                # section 中的键
                if config['section_name'] not in top_level_keys:
                    seen.add(key)
                    section_names.add(config['section_name'])
                    unique_configs.append(config)
    
    return unique_configs


def config_item_strategy():
    """生成配置项策略"""
    # 使用 flatmap 确保 value 和 data_type 匹配
    def generate_matching_value_and_type(data_type):
        if data_type == 'string':
            return st.fixed_dictionaries({
                'value': toml_string_strategy(),
                'data_type': st.just('string')
            })
        elif data_type == 'integer':
            return st.fixed_dictionaries({
                'value': toml_integer_strategy().map(str),
                'data_type': st.just('integer')
            })
        elif data_type == 'float':
            return st.fixed_dictionaries({
                'value': toml_float_strategy().map(str),
                'data_type': st.just('float')
            })
        else:  # boolean
            return st.fixed_dictionaries({
                'value': toml_boolean_strategy().map(lambda b: 'true' if b else 'false'),
                'data_type': st.just('boolean')
            })
    
    return st.sampled_from(['string', 'integer', 'float', 'boolean']).flatmap(
        lambda dt: st.fixed_dictionaries({
            'section_name': st.one_of(st.just(''), toml_section_strategy()),
            'key_name': toml_key_strategy(),
            'value_and_type': generate_matching_value_and_type(dt),
            'description': st.one_of(st.none(), toml_string_strategy())
        }).map(lambda d: {
            'section_name': d['section_name'],
            'key_name': d['key_name'],
            'value': d['value_and_type']['value'],
            'data_type': d['value_and_type']['data_type'],
            'description': d['description']
        })
    )


class TomlExporterPropertiesTest(TestCase):
    """TOML 导出服务属性测试类"""
    
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
    
    # ========== 属性 18: TOML 导出有效性 ==========
    
    @given(
        configs=st.lists(
            config_item_strategy(),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_18_toml_export_validity(self, configs):
        """属性 18: TOML 导出有效性
        
        Feature: persona-card-upload, Property 18: TOML 导出有效性
        **验证需求：5.3**
        
        对于任意 PersonaCardConfig 对象集合，美化打印器应将其格式化为语法有效的 TOML 文件。
        """
        # 确保至少有一个 version 字段
        has_version = any(
            config['key_name'] == 'version' and config['section_name'] == ''
            for config in configs
        )
        
        if not has_version:
            # 添加 version 字段
            configs = [
                {
                    'section_name': '',
                    'key_name': 'version',
                    'value': '1.0',
                    'data_type': 'string',
                    'description': None
                }
            ] + configs
        
        # 确保没有重复的 (section_name, key_name) 组合，并避免键名和 section 名冲突
        unique_configs = deduplicate_configs(configs)
        
        # 创建配置项
        for config in unique_configs:
            PersonaCardConfig.objects.create(
                persona_card=self.persona_card,
                section_name=config['section_name'],
                key_name=config['key_name'],
                value=config['value'],
                data_type=config['data_type'],
                description=config['description']
            )
        
        # 导出 TOML
        config_objects = PersonaCardConfig.objects.filter(persona_card=self.persona_card)
        toml_content = TomlExporterService.export_to_toml(config_objects)
        
        # 验证：导出的 TOML 应该是有效的
        try:
            parsed = tomllib.loads(toml_content)
            # 如果能成功解析，说明 TOML 格式有效
            self.assertIsNotNone(parsed, "导出的 TOML 应该能被成功解析")
        except tomllib.TOMLDecodeError as e:
            self.fail(f"导出的 TOML 格式无效: {e}\n内容:\n{toml_content}")
    
    # ========== 属性 19: 往返属性（解析-导出-解析）==========
    
    @given(
        configs=st.lists(
            config_item_strategy(),
            min_size=1,
            max_size=8
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_19_roundtrip(self, configs):
        """属性 19: 往返属性（解析-导出-解析）
        
        Feature: persona-card-upload, Property 19: 往返属性（解析-导出-解析）
        **验证需求：5.4**
        
        对于任意有效的 PersonaCardConfig 对象集合，
        执行"解析 → 美化打印 → 再解析"应产生等价的对象集合。
        """
        # 确保至少有一个 version 字段
        has_version = any(
            config['key_name'] == 'version' and config['section_name'] == ''
            for config in configs
        )
        
        if not has_version:
            configs = [
                {
                    'section_name': '',
                    'key_name': 'version',
                    'value': '1.0',
                    'data_type': 'string',
                    'description': None
                }
            ] + configs
        
        # 确保没有重复的 (section_name, key_name) 组合，并避免键名和 section 名冲突
        unique_configs = deduplicate_configs(configs)
        
        # 创建配置项
        for config in unique_configs:
            PersonaCardConfig.objects.create(
                persona_card=self.persona_card,
                section_name=config['section_name'],
                key_name=config['key_name'],
                value=config['value'],
                data_type=config['data_type'],
                description=config['description']
            )
        
        # 第一步：导出为 TOML
        config_objects = PersonaCardConfig.objects.filter(persona_card=self.persona_card)
        toml_content = TomlExporterService.export_to_toml(config_objects, include_deleted=False)
        
        # 第二步：解析 TOML
        try:
            parsed_data = TomlParserService.parse_content(toml_content)
        except Exception as e:
            self.fail(f"解析导出的 TOML 失败: {e}\n内容:\n{toml_content}")
        
        # 第三步：验证往返后数据等价
        # 构建原始配置的映射
        original_map = {}
        for config in unique_configs:
            section = config['section_name']
            key = config['key_name']
            original_map[(section, key)] = {
                'value': config['value'],
                'type': config['data_type']
            }
        
        # 构建解析后配置的映射
        parsed_map = {}
        for section in parsed_data['sections']:
            section_name = section['name']
            for item in section['items']:
                key = item['key']
                parsed_map[(section_name, key)] = {
                    'value': str(item['value']),
                    'type': item['type']
                }
        
        # 验证：所有原始配置项都应该在解析结果中
        for (section, key), original_item in original_map.items():
            self.assertIn(
                (section, key),
                parsed_map,
                f"配置项 {section}.{key} 在往返后丢失"
            )
            
            parsed_item = parsed_map[(section, key)]
            
            # 验证数据类型一致
            self.assertEqual(
                original_item['type'],
                parsed_item['type'],
                f"配置项 {section}.{key} 的类型在往返后改变"
            )
            
            # 验证值等价（考虑类型转换）
            original_value = original_item['value']
            parsed_value = parsed_item['value']
            
            if original_item['type'] == 'boolean':
                # 布尔值比较
                original_bool = original_value.lower() == 'true'
                parsed_bool = str(parsed_value).lower() == 'true'
                self.assertEqual(
                    original_bool,
                    parsed_bool,
                    f"配置项 {section}.{key} 的布尔值在往返后改变"
                )
            elif original_item['type'] in ['integer', 'float']:
                # 数值比较（允许浮点误差）
                try:
                    original_num = float(original_value)
                    parsed_num = float(parsed_value)
                    self.assertAlmostEqual(
                        original_num,
                        parsed_num,
                        places=5,
                        msg=f"配置项 {section}.{key} 的数值在往返后改变"
                    )
                except ValueError:
                    self.fail(f"配置项 {section}.{key} 的数值格式无效")
            else:
                # 字符串比较
                self.assertEqual(
                    original_value,
                    parsed_value,
                    f"配置项 {section}.{key} 的值在往返后改变"
                )
    
    # ========== 属性 20: 注释保留 ==========
    
    @given(
        configs=st.lists(
            st.fixed_dictionaries({
                'section_name': st.one_of(st.just(''), toml_section_strategy()),
                'key_name': toml_key_strategy(),
                'value': toml_string_strategy(),
                'data_type': st.just('string'),
                'description': toml_string_strategy()  # 确保有注释
            }),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_20_comment_preservation(self, configs):
        """属性 20: 注释保留
        
        Feature: persona-card-upload, Property 20: 注释保留
        **验证需求：5.5**
        
        对于任意包含注释的 PersonaCardConfig 对象集合，
        美化打印器导出的 TOML 文件应在相应配置项上方保留原始注释。
        """
        # 确保至少有一个 version 字段
        has_version = any(
            config['key_name'] == 'version' and config['section_name'] == ''
            for config in configs
        )
        
        if not has_version:
            configs = [
                {
                    'section_name': '',
                    'key_name': 'version',
                    'value': '1.0',
                    'data_type': 'string',
                    'description': '版本号注释'
                }
            ] + configs
        
        # 确保没有重复的 (section_name, key_name) 组合，并避免键名和 section 名冲突
        unique_configs = deduplicate_configs(configs)
        
        # 创建配置项
        for config in unique_configs:
            PersonaCardConfig.objects.create(
                persona_card=self.persona_card,
                section_name=config['section_name'],
                key_name=config['key_name'],
                value=config['value'],
                data_type=config['data_type'],
                description=config['description']
            )
        
        # 导出 TOML
        config_objects = PersonaCardConfig.objects.filter(persona_card=self.persona_card)
        toml_content = TomlExporterService.export_to_toml(config_objects)
        
        # 验证：所有注释都应该在导出的 TOML 中
        for config in unique_configs:
            description = config['description']
            if description:
                self.assertIn(
                    description,
                    toml_content,
                    f"注释 '{description}' 应该在导出的 TOML 中"
                )
                
                # 验证注释在配置项上方
                lines = toml_content.split('\n')
                key_name = config['key_name']
                
                for i, line in enumerate(lines):
                    if f'{key_name} =' in line:
                        # 找到配置项，检查上一行是否是注释
                        if i > 0:
                            prev_line = lines[i - 1]
                            if description in prev_line:
                                self.assertIn(
                                    '#',
                                    prev_line,
                                    f"注释行应该包含 # 符号"
                                )
                        break
    
    # ========== 属性 21: 被删除块处理 ==========
    
    @given(
        normal_configs=st.lists(
            config_item_strategy(),
            min_size=1,
            max_size=3
        ),
        deleted_sections=st.lists(
            toml_section_strategy(),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_21_deleted_block_handling(self, normal_configs, deleted_sections):
        """属性 21: 被删除块处理
        
        Feature: persona-card-upload, Property 21: 被删除块处理
        **验证需求：5.6**
        
        对于任意包含被删除配置块的 PersonaCardConfig 对象集合，
        美化打印器应在相应位置创建空块并添加注释 "# 此配置块已被作者删除"。
        """
        # 确保至少有一个 version 字段
        has_version = any(
            config['key_name'] == 'version' and config['section_name'] == ''
            for config in normal_configs
        )
        
        if not has_version:
            normal_configs = [
                {
                    'section_name': '',
                    'key_name': 'version',
                    'value': '1.0',
                    'data_type': 'string',
                    'description': None
                }
            ] + normal_configs
        
        # 确保没有重复的 (section_name, key_name) 组合，并避免键名和 section 名冲突
        unique_configs = deduplicate_configs(normal_configs)
        
        # 确保被删除的 section 不与正常 section 冲突，并去重
        normal_sections = {config['section_name'] for config in unique_configs}
        unique_deleted_sections = list(set([
            section for section in deleted_sections
            if section not in normal_sections and section  # 排除空 section
        ]))
        
        # 如果没有有效的被删除 section，跳过测试
        assume(len(unique_deleted_sections) > 0)
        
        # 创建正常配置项
        for config in unique_configs:
            PersonaCardConfig.objects.create(
                persona_card=self.persona_card,
                section_name=config['section_name'],
                key_name=config['key_name'],
                value=config['value'],
                data_type=config['data_type'],
                description=config['description'],
                is_deleted=False
            )
        
        # 创建被删除的配置项
        for section in unique_deleted_sections:
            PersonaCardConfig.objects.create(
                persona_card=self.persona_card,
                section_name=section,
                key_name='deleted_key',
                value='deleted_value',
                data_type='string',
                description=None,
                is_deleted=True
            )
        
        # 导出 TOML（包含被删除块）
        config_objects = PersonaCardConfig.objects.filter(persona_card=self.persona_card)
        toml_content = TomlExporterService.export_to_toml(config_objects, include_deleted=True)
        
        # 验证：所有被删除的 section 都应该在导出的 TOML 中
        for section in unique_deleted_sections:
            self.assertIn(
                f'[{section}]',
                toml_content,
                f"被删除的 section [{section}] 应该在导出的 TOML 中"
            )
            
            # 验证：被删除块应该有注释说明
            self.assertIn(
                '此配置块已被作者删除',
                toml_content,
                "应该包含被删除块的注释说明"
            )
        
        # 验证：被删除的配置项不应该出现
        self.assertNotIn(
            'deleted_key',
            toml_content,
            "被删除的配置项不应该出现在导出的 TOML 中"
        )
        
        # 验证：get_deleted_sections 方法应该返回正确的列表
        deleted_sections_list = TomlExporterService.get_deleted_sections(config_objects)
        
        for section in unique_deleted_sections:
            self.assertIn(
                section,
                deleted_sections_list,
                f"被删除的 section {section} 应该在 get_deleted_sections 返回的列表中"
            )
    
    @given(
        normal_configs=st.lists(
            config_item_strategy(),
            min_size=1,
            max_size=3
        ),
        deleted_sections=st.lists(
            toml_section_strategy(),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_21_deleted_block_exclusion(self, normal_configs, deleted_sections):
        """属性 21: 被删除块处理（不包含被删除块）
        
        Feature: persona-card-upload, Property 21: 被删除块处理
        **验证需求：5.6**
        
        当 include_deleted=False 时，被删除的配置块不应该出现在导出的 TOML 中。
        """
        # 确保至少有一个 version 字段
        has_version = any(
            config['key_name'] == 'version' and config['section_name'] == ''
            for config in normal_configs
        )
        
        if not has_version:
            normal_configs = [
                {
                    'section_name': '',
                    'key_name': 'version',
                    'value': '1.0',
                    'data_type': 'string',
                    'description': None
                }
            ] + normal_configs
        
        # 确保没有重复的 (section_name, key_name) 组合，并避免键名和 section 名冲突
        unique_configs = deduplicate_configs(normal_configs)
        
        # 确保被删除的 section 不与正常 section 冲突，并去重
        normal_sections = {config['section_name'] for config in unique_configs}
        unique_deleted_sections = list(set([
            section for section in deleted_sections
            if section not in normal_sections and section
        ]))
        
        assume(len(unique_deleted_sections) > 0)
        
        # 创建正常配置项
        for config in unique_configs:
            PersonaCardConfig.objects.create(
                persona_card=self.persona_card,
                section_name=config['section_name'],
                key_name=config['key_name'],
                value=config['value'],
                data_type=config['data_type'],
                description=config['description'],
                is_deleted=False
            )
        
        # 创建被删除的配置项
        for section in unique_deleted_sections:
            PersonaCardConfig.objects.create(
                persona_card=self.persona_card,
                section_name=section,
                key_name='deleted_key',
                value='deleted_value',
                data_type='string',
                description=None,
                is_deleted=True
            )
        
        # 导出 TOML（不包含被删除块）
        config_objects = PersonaCardConfig.objects.filter(persona_card=self.persona_card)
        toml_content = TomlExporterService.export_to_toml(config_objects, include_deleted=False)
        
        # 验证：被删除的 section 不应该在导出的 TOML 中
        for section in unique_deleted_sections:
            self.assertNotIn(
                f'[{section}]',
                toml_content,
                f"被删除的 section [{section}] 不应该在导出的 TOML 中（include_deleted=False）"
            )
        
        # 验证：不应该有被删除块的注释
        self.assertNotIn(
            '此配置块已被作者删除',
            toml_content,
            "不应该包含被删除块的注释说明（include_deleted=False）"
        )

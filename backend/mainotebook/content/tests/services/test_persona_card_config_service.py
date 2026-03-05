"""人设卡配置管理服务单元测试

测试配置管理服务的各项功能，包括：
- 批量创建配置项
- 批量更新配置项
- 获取配置项（包含和不包含已删除项）
- 复杂类型的序列化和反序列化
- 配置块删除标记

验证需求：6.1, 6.3, 6.5, 7.4
"""

import json
from django.test import TestCase
from mainotebook.system.models import Users
from mainotebook.content.models import PersonaCard, PersonaCardConfig
from mainotebook.content.services.persona_card_config_service import PersonaCardConfigService


class PersonaCardConfigServiceTest(TestCase):
    """配置管理服务单元测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建测试用户
        self.user = Users.objects.create(
            username="testuser",
            name="测试用户",
            email="test@example.com"
        )
        
        # 创建测试人设卡
        self.persona_card = PersonaCard.objects.create(
            name="测试人设卡",
            description="这是一个测试人设卡",
            uploader=self.user,
            version="1.0",
            creator=self.user,
            modifier=self.user
        )
    
    def tearDown(self):
        """测试后清理"""
        PersonaCardConfig.objects.all().delete()
        PersonaCard.objects.all().delete()
        Users.objects.all().delete()
    
    # ========== 批量创建配置项测试 ==========
    
    def test_create_configs_with_simple_types(self):
        """测试批量创建简单类型的配置项（需求 6.1）"""
        parsed_data = {
            'sections': [
                {
                    'name': 'inner.meta.card',
                    'comment': '人设卡元数据',
                    'items': [
                        {
                            'key': 'version',
                            'value': '1.0',
                            'type': 'string',
                            'comment': '版本号'
                        },
                        {
                            'key': 'name',
                            'value': '测试人设',
                            'type': 'string',
                            'comment': '人设名称'
                        }
                    ]
                },
                {
                    'name': 'settings',
                    'comment': '设置',
                    'items': [
                        {
                            'key': 'max_tokens',
                            'value': 2048,
                            'type': 'integer',
                            'comment': '最大令牌数'
                        },
                        {
                            'key': 'temperature',
                            'value': 0.7,
                            'type': 'float',
                            'comment': '温度参数'
                        },
                        {
                            'key': 'enabled',
                            'value': True,
                            'type': 'boolean',
                            'comment': '是否启用'
                        }
                    ]
                }
            ]
        }
        
        configs = PersonaCardConfigService.create_configs(
            self.persona_card,
            parsed_data,
            self.user
        )
        
        # 验证创建的配置项数量
        self.assertEqual(len(configs), 5)
        
        # 验证配置项内容
        version_config = PersonaCardConfig.objects.get(
            persona_card=self.persona_card,
            section_name='inner.meta.card',
            key_name='version'
        )
        self.assertEqual(version_config.value, '1.0')
        self.assertEqual(version_config.data_type, 'string')
        self.assertEqual(version_config.description, '版本号')
        
        max_tokens_config = PersonaCardConfig.objects.get(
            persona_card=self.persona_card,
            section_name='settings',
            key_name='max_tokens'
        )
        self.assertEqual(max_tokens_config.value, '2048')
        self.assertEqual(max_tokens_config.data_type, 'integer')
    
    def test_create_configs_with_complex_types(self):
        """测试批量创建复杂类型的配置项（需求 6.3）"""
        parsed_data = {
            'sections': [
                {
                    'name': 'prompts',
                    'comment': '提示词配置',
                    'items': [
                        {
                            'key': 'system_prompts',
                            'value': ['你是一个AI助手', '请友好地回答问题'],
                            'type': 'array',
                            'comment': '系统提示词列表'
                        },
                        {
                            'key': 'settings',
                            'value': {
                                'model': 'gpt-4',
                                'max_tokens': 2048,
                                'temperature': 0.7
                            },
                            'type': 'object',
                            'comment': '设置对象'
                        }
                    ]
                }
            ]
        }
        
        configs = PersonaCardConfigService.create_configs(
            self.persona_card,
            parsed_data,
            self.user
        )
        
        # 验证数组类型序列化
        array_config = PersonaCardConfig.objects.get(
            persona_card=self.persona_card,
            section_name='prompts',
            key_name='system_prompts'
        )
        self.assertEqual(array_config.data_type, 'array')
        # 验证值被序列化为 JSON 字符串
        stored_value = json.loads(array_config.value)
        self.assertEqual(stored_value, ['你是一个AI助手', '请友好地回答问题'])
        
        # 验证对象类型序列化
        object_config = PersonaCardConfig.objects.get(
            persona_card=self.persona_card,
            section_name='prompts',
            key_name='settings'
        )
        self.assertEqual(object_config.data_type, 'object')
        stored_value = json.loads(object_config.value)
        self.assertEqual(stored_value['model'], 'gpt-4')
        self.assertEqual(stored_value['max_tokens'], 2048)
    
    def test_create_configs_with_missing_sections(self):
        """测试创建配置项时缺少 sections 字段"""
        parsed_data = {}
        
        with self.assertRaises(ValueError) as context:
            PersonaCardConfigService.create_configs(
                self.persona_card,
                parsed_data,
                self.user
            )
        
        self.assertIn("缺少 'sections' 字段", str(context.exception))
    
    def test_create_configs_uses_section_comment_when_item_has_no_comment(self):
        """测试当配置项没有注释时使用块注释"""
        parsed_data = {
            'sections': [
                {
                    'name': 'test_section',
                    'comment': '这是块注释',
                    'items': [
                        {
                            'key': 'key1',
                            'value': 'value1',
                            'type': 'string',
                            'comment': ''  # 空注释
                        }
                    ]
                }
            ]
        }
        
        configs = PersonaCardConfigService.create_configs(
            self.persona_card,
            parsed_data,
            self.user
        )
        
        config = PersonaCardConfig.objects.get(
            persona_card=self.persona_card,
            section_name='test_section',
            key_name='key1'
        )
        # 应该使用块注释
        self.assertEqual(config.description, '这是块注释')
    
    # ========== 批量更新配置项测试 ==========
    
    def test_update_configs_value(self):
        """测试批量更新配置项的值（需求 6.5）"""
        # 先创建配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='settings',
            key_name='max_tokens',
            value='2048',
            data_type='integer',
            creator=self.user,
            modifier=self.user
        )
        
        # 更新配置项
        updates = [
            {
                'section': 'settings',
                'key': 'max_tokens',
                'value': '4096'
            }
        ]
        
        updated_configs = PersonaCardConfigService.update_configs(
            self.persona_card,
            updates,
            self.user
        )
        
        # 验证更新成功
        self.assertEqual(len(updated_configs), 1)
        
        config = PersonaCardConfig.objects.get(
            persona_card=self.persona_card,
            section_name='settings',
            key_name='max_tokens'
        )
        self.assertEqual(config.value, '4096')
        self.assertEqual(config.modifier, self.user.username)
    
    def test_update_configs_comment(self):
        """测试批量更新配置项的注释"""
        # 先创建配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='settings',
            key_name='temperature',
            value='0.7',
            data_type='float',
            description='旧注释',
            creator=self.user,
            modifier=self.user
        )
        
        # 更新注释
        updates = [
            {
                'section': 'settings',
                'key': 'temperature',
                'comment': '新注释：温度参数'
            }
        ]
        
        updated_configs = PersonaCardConfigService.update_configs(
            self.persona_card,
            updates,
            self.user
        )
        
        config = PersonaCardConfig.objects.get(
            persona_card=self.persona_card,
            section_name='settings',
            key_name='temperature'
        )
        self.assertEqual(config.description, '新注释：温度参数')
    
    def test_update_configs_complex_type(self):
        """测试更新复杂类型的配置项（需求 6.3）"""
        # 先创建数组类型配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='prompts',
            key_name='system_prompts',
            value=json.dumps(['旧提示词']),
            data_type='array',
            creator=self.user,
            modifier=self.user
        )
        
        # 更新为新的数组
        updates = [
            {
                'section': 'prompts',
                'key': 'system_prompts',
                'value': ['新提示词1', '新提示词2']
            }
        ]
        
        updated_configs = PersonaCardConfigService.update_configs(
            self.persona_card,
            updates,
            self.user
        )
        
        config = PersonaCardConfig.objects.get(
            persona_card=self.persona_card,
            section_name='prompts',
            key_name='system_prompts'
        )
        stored_value = json.loads(config.value)
        self.assertEqual(stored_value, ['新提示词1', '新提示词2'])
    
    def test_update_configs_is_deleted(self):
        """测试更新配置项的删除标记（需求 7.4）"""
        # 先创建配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='settings',
            key_name='enabled',
            value='true',
            data_type='boolean',
            is_deleted=False,
            creator=self.user,
            modifier=self.user
        )
        
        # 标记为删除
        updates = [
            {
                'section': 'settings',
                'key': 'enabled',
                'is_deleted': True
            }
        ]
        
        updated_configs = PersonaCardConfigService.update_configs(
            self.persona_card,
            updates,
            self.user
        )
        
        config = PersonaCardConfig.objects.get(
            persona_card=self.persona_card,
            section_name='settings',
            key_name='enabled'
        )
        self.assertTrue(config.is_deleted)
    
    def test_update_configs_nonexistent_config(self):
        """测试更新不存在的配置项"""
        updates = [
            {
                'section': 'nonexistent',
                'key': 'nonexistent_key',
                'value': 'value'
            }
        ]
        
        with self.assertRaises(ValueError) as context:
            PersonaCardConfigService.update_configs(
                self.persona_card,
                updates,
                self.user
            )
        
        self.assertIn("配置项不存在", str(context.exception))
    
    # ========== 获取配置项测试 ==========
    
    def test_get_configs_exclude_deleted(self):
        """测试获取配置项（不包含已删除项）（需求 6.1）"""
        # 创建配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='settings',
            key_name='key1',
            value='value1',
            data_type='string',
            is_deleted=False,
            creator=self.user,
            modifier=self.user
        )
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='settings',
            key_name='key2',
            value='value2',
            data_type='string',
            is_deleted=True,  # 已删除
            creator=self.user,
            modifier=self.user
        )
        
        # 获取配置项（不包含已删除）
        configs = PersonaCardConfigService.get_configs(
            self.persona_card,
            include_deleted=False
        )
        
        # 应该只返回未删除的配置项
        self.assertEqual(configs.count(), 1)
        self.assertEqual(configs.first().key_name, 'key1')
    
    def test_get_configs_include_deleted(self):
        """测试获取配置项（包含已删除项）"""
        # 创建配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='settings',
            key_name='key1',
            value='value1',
            data_type='string',
            is_deleted=False,
            creator=self.user,
            modifier=self.user
        )
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='settings',
            key_name='key2',
            value='value2',
            data_type='string',
            is_deleted=True,
            creator=self.user,
            modifier=self.user
        )
        
        # 获取配置项（包含已删除）
        configs = PersonaCardConfigService.get_configs(
            self.persona_card,
            include_deleted=True
        )
        
        # 应该返回所有配置项
        self.assertEqual(configs.count(), 2)
    
    def test_get_configs_by_section(self):
        """测试获取指定配置块的配置项"""
        # 创建不同配置块的配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='section1',
            key_name='key1',
            value='value1',
            data_type='string',
            creator=self.user,
            modifier=self.user
        )
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='section2',
            key_name='key2',
            value='value2',
            data_type='string',
            creator=self.user,
            modifier=self.user
        )
        
        # 获取 section1 的配置项
        configs = PersonaCardConfigService.get_configs_by_section(
            self.persona_card,
            'section1'
        )
        
        self.assertEqual(configs.count(), 1)
        self.assertEqual(configs.first().section_name, 'section1')
    
    # ========== 配置块删除测试 ==========
    
    def test_delete_section(self):
        """测试标记配置块为已删除（需求 7.4）"""
        # 创建同一配置块的多个配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='test_section',
            key_name='key1',
            value='value1',
            data_type='string',
            creator=self.user,
            modifier=self.user
        )
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='test_section',
            key_name='key2',
            value='value2',
            data_type='string',
            creator=self.user,
            modifier=self.user
        )
        
        # 删除配置块
        count = PersonaCardConfigService.delete_section(
            self.persona_card,
            'test_section',
            self.user
        )
        
        # 验证删除数量
        self.assertEqual(count, 2)
        
        # 验证所有配置项都被标记为删除
        configs = PersonaCardConfig.objects.filter(
            persona_card=self.persona_card,
            section_name='test_section'
        )
        for config in configs:
            self.assertTrue(config.is_deleted)
    
    # ========== 值反序列化测试 ==========
    
    def test_get_value_string(self):
        """测试获取字符串类型的值"""
        config = PersonaCardConfig(
            value='test string',
            data_type='string'
        )
        value = PersonaCardConfigService.get_value(config)
        self.assertEqual(value, 'test string')
    
    def test_get_value_integer(self):
        """测试获取整数类型的值"""
        config = PersonaCardConfig(
            value='2048',
            data_type='integer'
        )
        value = PersonaCardConfigService.get_value(config)
        self.assertEqual(value, 2048)
        self.assertIsInstance(value, int)
    
    def test_get_value_float(self):
        """测试获取浮点数类型的值"""
        config = PersonaCardConfig(
            value='0.7',
            data_type='float'
        )
        value = PersonaCardConfigService.get_value(config)
        self.assertEqual(value, 0.7)
        self.assertIsInstance(value, float)
    
    def test_get_value_boolean(self):
        """测试获取布尔类型的值"""
        config_true = PersonaCardConfig(
            value='true',
            data_type='boolean'
        )
        value_true = PersonaCardConfigService.get_value(config_true)
        self.assertTrue(value_true)
        
        config_false = PersonaCardConfig(
            value='false',
            data_type='boolean'
        )
        value_false = PersonaCardConfigService.get_value(config_false)
        self.assertFalse(value_false)
    
    def test_get_value_array(self):
        """测试获取数组类型的值（需求 6.3）"""
        config = PersonaCardConfig(
            value=json.dumps(['item1', 'item2', 'item3']),
            data_type='array'
        )
        value = PersonaCardConfigService.get_value(config)
        self.assertEqual(value, ['item1', 'item2', 'item3'])
        self.assertIsInstance(value, list)
    
    def test_get_value_object(self):
        """测试获取对象类型的值（需求 6.3）"""
        config = PersonaCardConfig(
            value=json.dumps({'key1': 'value1', 'key2': 123}),
            data_type='object'
        )
        value = PersonaCardConfigService.get_value(config)
        self.assertEqual(value, {'key1': 'value1', 'key2': 123})
        self.assertIsInstance(value, dict)
    
    # ========== 格式化配置项测试 ==========
    
    def test_format_configs_as_dict(self):
        """测试将配置项格式化为字典结构"""
        # 创建配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='section1',
            key_name='key1',
            value='value1',
            data_type='string',
            description='注释1',
            is_deleted=False,
            creator=self.user,
            modifier=self.user
        )
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='section1',
            key_name='key2',
            value='2048',
            data_type='integer',
            description='注释2',
            is_deleted=False,
            creator=self.user,
            modifier=self.user
        )
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name='section2',
            key_name='key3',
            value=json.dumps(['a', 'b']),
            data_type='array',
            description='注释3',
            is_deleted=False,
            creator=self.user,
            modifier=self.user
        )
        
        # 获取并格式化配置项
        configs = PersonaCardConfigService.get_configs(self.persona_card)
        formatted = PersonaCardConfigService.format_configs_as_dict(configs)
        
        # 验证格式化结果
        self.assertIn('sections', formatted)
        self.assertEqual(len(formatted['sections']), 2)
        
        # 验证 section1
        section1 = next(s for s in formatted['sections'] if s['name'] == 'section1')
        self.assertEqual(len(section1['items']), 2)
        
        # 验证配置项内容
        key1_item = next(item for item in section1['items'] if item['key'] == 'key1')
        self.assertEqual(key1_item['value'], 'value1')
        self.assertEqual(key1_item['type'], 'string')
        self.assertEqual(key1_item['comment'], '注释1')
        self.assertFalse(key1_item['is_deleted'])
        
        key2_item = next(item for item in section1['items'] if item['key'] == 'key2')
        self.assertEqual(key2_item['value'], 2048)  # 应该被反序列化为整数
        
        # 验证 section2
        section2 = next(s for s in formatted['sections'] if s['name'] == 'section2')
        key3_item = section2['items'][0]
        self.assertEqual(key3_item['value'], ['a', 'b'])  # 应该被反序列化为列表

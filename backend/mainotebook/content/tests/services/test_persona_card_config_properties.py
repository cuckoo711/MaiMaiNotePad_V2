"""人设卡配置管理服务属性测试

使用 Hypothesis 进行基于属性的测试，验证配置管理服务的正确性属性。

**验证需求：6.3, 6.5, 7.4**

属性列表：
- 属性 22: 复杂类型序列化
- 属性 23: 配置项更新
- 属性 24: 配置块删除标记
"""

import json
from hypothesis import given, settings, strategies as st, assume
from hypothesis.extra.django import TestCase

from mainotebook.system.models import Users
from mainotebook.content.models import PersonaCard, PersonaCardConfig
from mainotebook.content.services.persona_card_config_service import PersonaCardConfigService


# 配置 Hypothesis
settings.register_profile("default", max_examples=100, deadline=None)
settings.load_profile("default")


# 策略定义
def json_serializable_array_strategy():
    """生成可 JSON 序列化的数组"""
    return st.lists(
        st.one_of(
            st.text(min_size=0, max_size=50),
            st.integers(min_value=-1000, max_value=1000),
            st.floats(
                min_value=-1000.0,
                max_value=1000.0,
                allow_nan=False,
                allow_infinity=False
            ),
            st.booleans()
        ),
        min_size=0,
        max_size=10
    )


def json_serializable_object_strategy():
    """生成可 JSON 序列化的对象"""
    return st.dictionaries(
        keys=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz_',
            min_size=1,
            max_size=20
        ),
        values=st.one_of(
            st.text(min_size=0, max_size=50),
            st.integers(min_value=-1000, max_value=1000),
            st.floats(
                min_value=-1000.0,
                max_value=1000.0,
                allow_nan=False,
                allow_infinity=False
            ),
            st.booleans()
        ),
        min_size=1,
        max_size=5
    )


def section_name_strategy():
    """生成有效的配置块名称"""
    return st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz._',
        min_size=1,
        max_size=50
    ).filter(lambda x: x and x[0].isalpha())


def key_name_strategy():
    """生成有效的配置键名"""
    return st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz_',
        min_size=1,
        max_size=50
    ).filter(lambda x: x and x[0].isalpha())


class PersonaCardConfigPropertiesTest(TestCase):
    """配置管理服务属性测试类"""
    
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
            modifier=self.user.username
        )
    
    def tearDown(self):
        """测试后清理"""
        PersonaCardConfig.objects.all().delete()
        PersonaCard.objects.all().delete()
        Users.objects.all().delete()
    
    # ========== 属性 22: 复杂类型序列化 ==========
    
    @settings(max_examples=50)
    @given(array_value=json_serializable_array_strategy())
    def test_property_22_array_serialization_roundtrip(self, array_value):
        """
        Feature: persona-card-upload, Property 22: 复杂类型序列化
        
        对于任意数据类型为 array 的配置项，系统应将其值序列化为 JSON 字符串存储，
        并能正确反序列化。
        
        验证需求：6.3
        """
        # 创建数组类型配置项
        parsed_data = {
            'sections': [
                {
                    'name': 'test_section',
                    'comment': '测试块',
                    'items': [
                        {
                            'key': 'test_array',
                            'value': array_value,
                            'type': 'array',
                            'comment': '测试数组'
                        }
                    ]
                }
            ]
        }
        
        # 创建配置项
        configs = PersonaCardConfigService.create_configs(
            self.persona_card,
            parsed_data,
            self.user
        )
        
        # 验证配置项被创建
        self.assertEqual(len(configs), 1)
        config = configs[0]
        
        # 验证值被序列化为 JSON 字符串
        self.assertIsInstance(config.value, str)
        
        # 验证可以反序列化
        deserialized_value = PersonaCardConfigService.get_value(config)
        
        # 验证往返后值相等
        self.assertEqual(deserialized_value, array_value)
    
    @settings(max_examples=50)
    @given(object_value=json_serializable_object_strategy())
    def test_property_22_object_serialization_roundtrip(self, object_value):
        """
        Feature: persona-card-upload, Property 22: 复杂类型序列化
        
        对于任意数据类型为 object 的配置项，系统应将其值序列化为 JSON 字符串存储，
        并能正确反序列化。
        
        验证需求：6.3
        """
        # 创建对象类型配置项
        parsed_data = {
            'sections': [
                {
                    'name': 'test_section',
                    'comment': '测试块',
                    'items': [
                        {
                            'key': 'test_object',
                            'value': object_value,
                            'type': 'object',
                            'comment': '测试对象'
                        }
                    ]
                }
            ]
        }
        
        # 创建配置项
        configs = PersonaCardConfigService.create_configs(
            self.persona_card,
            parsed_data,
            self.user
        )
        
        # 验证配置项被创建
        self.assertEqual(len(configs), 1)
        config = configs[0]
        
        # 验证值被序列化为 JSON 字符串
        self.assertIsInstance(config.value, str)
        
        # 验证可以反序列化
        deserialized_value = PersonaCardConfigService.get_value(config)
        
        # 验证往返后值相等
        self.assertEqual(deserialized_value, object_value)
    
    # ========== 属性 23: 配置项更新 ==========
    
    @settings(max_examples=50)
    @given(
        section_name=section_name_strategy(),
        key_name=key_name_strategy(),
        initial_value=st.text(
            min_size=1,
            max_size=100,
            alphabet=st.characters(blacklist_characters='\x00')
        ),
        new_value=st.text(
            min_size=1,
            max_size=100,
            alphabet=st.characters(blacklist_characters='\x00')
        )
    )
    def test_property_23_config_update_records_modification(
        self,
        section_name,
        key_name,
        initial_value,
        new_value
    ):
        """
        Feature: persona-card-upload, Property 23: 配置项更新
        
        对于任意配置项的更新请求，系统应更新对应的 PersonaCardConfig 实例，
        并记录更新时间。
        
        验证需求：6.5
        """
        # 假设初始值和新值不同
        assume(initial_value != new_value)
        
        # 创建初始配置项
        config = PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name=section_name,
            key_name=key_name,
            value=initial_value,
            data_type='string',
            creator=self.user,
            modifier=self.user.username
        )
        
        # 记录初始更新时间
        initial_update_time = config.update_datetime
        
        # 更新配置项
        updates = [
            {
                'section': section_name,
                'key': key_name,
                'value': new_value
            }
        ]
        
        updated_configs = PersonaCardConfigService.update_configs(
            self.persona_card,
            updates,
            self.user
        )
        
        # 验证更新成功
        self.assertEqual(len(updated_configs), 1)
        
        # 重新获取配置项
        config.refresh_from_db()
        
        # 验证值已更新
        self.assertEqual(config.value, new_value)
        
        # 验证修改者已更新
        self.assertEqual(config.modifier, self.user.username)
        
        # 验证更新时间已改变
        self.assertIsNotNone(config.update_datetime)
        if initial_update_time:
            self.assertGreaterEqual(config.update_datetime, initial_update_time)
    
    @settings(max_examples=50)
    @given(
        section_name=section_name_strategy(),
        key_name=key_name_strategy(),
        initial_comment=st.text(
            min_size=0,
            max_size=100,
            alphabet=st.characters(blacklist_characters='\x00')
        ),
        new_comment=st.text(
            min_size=0,
            max_size=100,
            alphabet=st.characters(blacklist_characters='\x00')
        )
    )
    def test_property_23_config_comment_update(
        self,
        section_name,
        key_name,
        initial_comment,
        new_comment
    ):
        """
        Feature: persona-card-upload, Property 23: 配置项更新
        
        对于任意配置项的注释更新请求，系统应更新对应的 description 字段。
        
        验证需求：6.5, 7.5
        """
        # 假设注释不同
        assume(initial_comment != new_comment)
        
        # 创建初始配置项
        config = PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name=section_name,
            key_name=key_name,
            value='test_value',
            data_type='string',
            description=initial_comment,
            creator=self.user,
            modifier=self.user.username
        )
        
        # 更新注释
        updates = [
            {
                'section': section_name,
                'key': key_name,
                'comment': new_comment
            }
        ]
        
        updated_configs = PersonaCardConfigService.update_configs(
            self.persona_card,
            updates,
            self.user
        )
        
        # 验证更新成功
        self.assertEqual(len(updated_configs), 1)
        
        # 重新获取配置项
        config.refresh_from_db()
        
        # 验证注释已更新
        self.assertEqual(config.description, new_comment)
    
    # ========== 属性 24: 配置块删除标记 ==========
    
    @settings(max_examples=50)
    @given(
        section_name=section_name_strategy(),
        num_keys=st.integers(min_value=1, max_value=10)
    )
    def test_property_24_section_deletion_marks_all_items(
        self,
        section_name,
        num_keys
    ):
        """
        Feature: persona-card-upload, Property 24: 配置块删除标记
        
        对于任意配置块的删除操作，系统应将该块下所有配置项的 is_deleted 字段
        设置为 True，而不是物理删除。
        
        验证需求：7.4
        """
        # 创建多个配置项
        for i in range(num_keys):
            PersonaCardConfig.objects.create(
                persona_card=self.persona_card,
                section_name=section_name,
                key_name=f'key_{i}',
                value=f'value_{i}',
                data_type='string',
                is_deleted=False,
                creator=self.user,
                modifier=self.user.username
            )
        
        # 删除配置块
        count = PersonaCardConfigService.delete_section(
            self.persona_card,
            section_name,
            self.user
        )
        
        # 验证删除数量
        self.assertEqual(count, num_keys)
        
        # 验证所有配置项都被标记为删除
        configs = PersonaCardConfig.objects.filter(
            persona_card=self.persona_card,
            section_name=section_name
        )
        
        self.assertEqual(configs.count(), num_keys)
        for config in configs:
            self.assertTrue(config.is_deleted)
            # 验证配置项仍然存在（软删除）
            self.assertIsNotNone(config.id)
    
    @settings(max_examples=50)
    @given(
        section_name=section_name_strategy(),
        key_name=key_name_strategy()
    )
    def test_property_24_individual_item_deletion_mark(
        self,
        section_name,
        key_name
    ):
        """
        Feature: persona-card-upload, Property 24: 配置块删除标记
        
        对于任意单个配置项的删除操作，系统应将其 is_deleted 字段设置为 True。
        
        验证需求：7.4
        """
        # 创建配置项
        config = PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name=section_name,
            key_name=key_name,
            value='test_value',
            data_type='string',
            is_deleted=False,
            creator=self.user,
            modifier=self.user.username
        )
        
        # 标记为删除
        updates = [
            {
                'section': section_name,
                'key': key_name,
                'is_deleted': True
            }
        ]
        
        updated_configs = PersonaCardConfigService.update_configs(
            self.persona_card,
            updates,
            self.user
        )
        
        # 验证更新成功
        self.assertEqual(len(updated_configs), 1)
        
        # 重新获取配置项
        config.refresh_from_db()
        
        # 验证被标记为删除
        self.assertTrue(config.is_deleted)
        
        # 验证配置项仍然存在（软删除）
        self.assertIsNotNone(config.id)
        exists = PersonaCardConfig.objects.filter(id=config.id).exists()
        self.assertTrue(exists)
    
    @settings(max_examples=50)
    @given(
        section_name=section_name_strategy(),
        key_name=key_name_strategy()
    )
    def test_property_24_deleted_items_excluded_by_default(
        self,
        section_name,
        key_name
    ):
        """
        Feature: persona-card-upload, Property 24: 配置块删除标记
        
        对于任意被标记为删除的配置项，在默认查询时应被排除。
        
        验证需求：7.4
        """
        # 创建已删除的配置项
        PersonaCardConfig.objects.create(
            persona_card=self.persona_card,
            section_name=section_name,
            key_name=key_name,
            value='test_value',
            data_type='string',
            is_deleted=True,
            creator=self.user,
            modifier=self.user.username
        )
        
        # 获取配置项（不包含已删除）
        configs = PersonaCardConfigService.get_configs(
            self.persona_card,
            include_deleted=False
        )
        
        # 验证已删除的配置项不在结果中
        matching_configs = [
            c for c in configs
            if c.section_name == section_name and c.key_name == key_name
        ]
        self.assertEqual(len(matching_configs), 0)
        
        # 获取配置项（包含已删除）
        configs_with_deleted = PersonaCardConfigService.get_configs(
            self.persona_card,
            include_deleted=True
        )
        
        # 验证已删除的配置项在结果中
        matching_configs_with_deleted = [
            c for c in configs_with_deleted
            if c.section_name == section_name and c.key_name == key_name
        ]
        self.assertEqual(len(matching_configs_with_deleted), 1)

"""敏感信息检测服务单元测试

测试敏感信息检测服务的各项功能，包括：
- 测试检测 5 位数字
- 测试检测 11 位数字
- 测试不检测 4 位数字
- 测试不检测 12 位数字
- 测试检测多个敏感信息
- 测试生成确认声明文本

**验证需求：8.1, 8.2, 8.4**
"""

from django.test import TestCase

from mainotebook.content.services.sensitive_info_detector_service import SensitiveInfoDetectorService


class SensitiveInfoDetectorServiceTest(TestCase):
    """敏感信息检测服务单元测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.detector = SensitiveInfoDetectorService()
    
    # ========== 检测 5 位数字测试 ==========
    
    def test_detect_5_digit_number(self):
        """测试检测 5 位数字（需求 8.1）"""
        configs = [
            {
                'section': 'contact',
                'key': 'qq',
                'value': '12345'
            }
        ]
        
        result = self.detector.detect(configs)
        
        # 验证检测到敏感信息
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['section'], 'contact')
        self.assertEqual(result[0]['key'], 'qq')
        self.assertIn('12345', result[0]['matches'])
        self.assertEqual(result[0]['path'], 'contact.qq')
    
    def test_detect_5_digit_in_text(self):
        """测试检测文本中的 5 位数字（需求 8.1）"""
        configs = [
            {
                'section': 'info',
                'key': 'description',
                'value': '请联系 QQ: 54321 获取更多信息'
            }
        ]
        
        result = self.detector.detect(configs)
        
        # 验证检测到敏感信息
        self.assertEqual(len(result), 1)
        self.assertIn('54321', result[0]['matches'])
    
    # ========== 检测 11 位数字测试 ==========
    
    def test_detect_11_digit_number(self):
        """测试检测 11 位数字（需求 8.2）"""
        configs = [
            {
                'section': 'contact',
                'key': 'qq',
                'value': '12345678901'
            }
        ]
        
        result = self.detector.detect(configs)
        
        # 验证检测到敏感信息
        self.assertEqual(len(result), 1)
        self.assertIn('12345678901', result[0]['matches'])
    
    def test_detect_11_digit_in_text(self):
        """测试检测文本中的 11 位数字（需求 8.2）"""
        configs = [
            {
                'section': 'info',
                'key': 'description',
                'value': '加入 QQ 群 98765432109 讨论'
            }
        ]
        
        result = self.detector.detect(configs)
        
        # 验证检测到敏感信息
        self.assertEqual(len(result), 1)
        self.assertIn('98765432109', result[0]['matches'])
    
    # ========== 不检测 4 位数字测试 ==========
    
    def test_no_detection_for_4_digit_number(self):
        """测试不检测 4 位数字（需求 8.1）"""
        configs = [
            {
                'section': 'settings',
                'key': 'year',
                'value': '2024'
            }
        ]
        
        result = self.detector.detect(configs)
        
        # 验证没有检测到敏感信息
        self.assertEqual(len(result), 0)
    
    def test_no_detection_for_4_digit_in_text(self):
        """测试不检测文本中的 4 位数字（需求 8.1）"""
        configs = [
            {
                'section': 'info',
                'key': 'description',
                'value': '成立于 2024 年，拥有 1000 名用户'
            }
        ]
        
        result = self.detector.detect(configs)
        
        # 验证没有检测到敏感信息
        self.assertEqual(len(result), 0)
    
    # ========== 不检测 12 位数字测试 ==========
    
    def test_no_detection_for_12_digit_number(self):
        """测试不检测 12 位数字（需求 8.2）"""
        configs = [
            {
                'section': 'settings',
                'key': 'timestamp',
                'value': '123456789012'
            }
        ]
        
        result = self.detector.detect(configs)
        
        # 验证没有检测到敏感信息
        self.assertEqual(len(result), 0)
    
    def test_no_detection_for_12_digit_in_text(self):
        """测试不检测文本中的 12 位数字（需求 8.2）"""
        configs = [
            {
                'section': 'info',
                'key': 'description',
                'value': '订单号：987654321098'
            }
        ]
        
        result = self.detector.detect(configs)
        
        # 验证没有检测到敏感信息
        self.assertEqual(len(result), 0)
    
    # ========== 检测多个敏感信息测试 ==========
    
    def test_detect_multiple_sensitive_items(self):
        """测试检测多个敏感信息（需求 8.4）"""
        configs = [
            {
                'section': 'contact',
                'key': 'qq',
                'value': '12345'
            },
            {
                'section': 'contact',
                'key': 'group',
                'value': '9876543210'
            },
            {
                'section': 'info',
                'key': 'description',
                'value': '联系 QQ: 11111 或加入群 222222'
            }
        ]
        
        result = self.detector.detect(configs)
        
        # 验证检测到 3 个配置项包含敏感信息
        self.assertEqual(len(result), 3)
        
        # 验证第一个配置项
        self.assertEqual(result[0]['path'], 'contact.qq')
        self.assertIn('12345', result[0]['matches'])
        
        # 验证第二个配置项
        self.assertEqual(result[1]['path'], 'contact.group')
        self.assertIn('9876543210', result[1]['matches'])
        
        # 验证第三个配置项（包含两个敏感数字）
        self.assertEqual(result[2]['path'], 'info.description')
        self.assertIn('11111', result[2]['matches'])
        self.assertIn('222222', result[2]['matches'])
    
    def test_detect_multiple_numbers_in_single_value(self):
        """测试检测单个值中的多个敏感数字（需求 8.4）"""
        configs = [
            {
                'section': 'contact',
                'key': 'info',
                'value': 'QQ1: 12345, QQ2: 67890, 群号: 1234567890'
            }
        ]
        
        result = self.detector.detect(configs)
        
        # 验证检测到 1 个配置项
        self.assertEqual(len(result), 1)
        
        # 验证检测到 3 个敏感数字
        self.assertEqual(len(result[0]['matches']), 3)
        self.assertIn('12345', result[0]['matches'])
        self.assertIn('67890', result[0]['matches'])
        self.assertIn('1234567890', result[0]['matches'])
    
    # ========== 生成确认声明文本测试 ==========
    
    def test_generate_confirmation_text_single_item(self):
        """测试生成单个敏感信息的确认声明（需求 8.4）"""
        sensitive_items = [
            {
                'section': 'contact',
                'key': 'qq',
                'value': '12345',
                'matches': ['12345'],
                'path': 'contact.qq'
            }
        ]
        
        text = self.detector.generate_confirmation_text(sensitive_items)
        
        # 验证确认声明包含配置项路径
        self.assertIn('contact.qq', text)
        self.assertIn('不涉及个人隐私信息', text)
    
    def test_generate_confirmation_text_multiple_items(self):
        """测试生成多个敏感信息的确认声明（需求 8.4）"""
        sensitive_items = [
            {
                'section': 'contact',
                'key': 'qq',
                'value': '12345',
                'matches': ['12345'],
                'path': 'contact.qq'
            },
            {
                'section': 'contact',
                'key': 'group',
                'value': '9876543210',
                'matches': ['9876543210'],
                'path': 'contact.group'
            },
            {
                'section': 'info',
                'key': 'description',
                'value': '联系 QQ: 11111',
                'matches': ['11111'],
                'path': 'info.description'
            }
        ]
        
        text = self.detector.generate_confirmation_text(sensitive_items)
        
        # 验证确认声明包含所有配置项路径
        self.assertIn('contact.qq', text)
        self.assertIn('contact.group', text)
        self.assertIn('info.description', text)
        self.assertIn('不涉及个人隐私信息', text)
    
    def test_generate_confirmation_text_empty_list(self):
        """测试生成空列表的确认声明"""
        sensitive_items = []
        
        text = self.detector.generate_confirmation_text(sensitive_items)
        
        # 验证返回空字符串
        self.assertEqual(text, '')
    
    # ========== detect_from_sections 方法测试 ==========
    
    def test_detect_from_sections(self):
        """测试从配置块列表中检测敏感信息"""
        sections = [
            {
                'name': 'contact',
                'items': [
                    {
                        'key': 'qq',
                        'value': '12345'
                    },
                    {
                        'key': 'email',
                        'value': 'test@example.com'
                    }
                ]
            },
            {
                'name': 'info',
                'items': [
                    {
                        'key': 'description',
                        'value': '加入群 9876543210'
                    }
                ]
            }
        ]
        
        result = self.detector.detect_from_sections(sections)
        
        # 验证检测到 2 个配置项包含敏感信息
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['path'], 'contact.qq')
        self.assertEqual(result[1]['path'], 'info.description')
    
    # ========== get_sensitive_locations 方法测试 ==========
    
    def test_get_sensitive_locations(self):
        """测试获取敏感信息位置列表"""
        sensitive_items = [
            {
                'section': 'contact',
                'key': 'qq',
                'value': '12345',
                'matches': ['12345'],
                'path': 'contact.qq'
            },
            {
                'section': 'info',
                'key': 'description',
                'value': 'QQ: 11111 群: 222222',
                'matches': ['11111', '222222'],
                'path': 'info.description'
            }
        ]
        
        locations = self.detector.get_sensitive_locations(sensitive_items)
        
        # 验证位置列表
        self.assertEqual(len(locations), 2)
        
        # 验证第一个位置
        self.assertEqual(locations[0]['path'], 'contact.qq')
        self.assertEqual(locations[0]['matches'], ['12345'])
        
        # 验证第二个位置
        self.assertEqual(locations[1]['path'], 'info.description')
        self.assertEqual(locations[1]['matches'], ['11111', '222222'])
    
    # ========== 边缘情况测试 ==========
    
    def test_detect_with_empty_configs(self):
        """测试检测空配置列表"""
        configs = []
        
        result = self.detector.detect(configs)
        
        # 验证返回空列表
        self.assertEqual(len(result), 0)
    
    def test_detect_with_empty_value(self):
        """测试检测空值"""
        configs = [
            {
                'section': 'test',
                'key': 'empty',
                'value': ''
            }
        ]
        
        result = self.detector.detect(configs)
        
        # 验证没有检测到敏感信息
        self.assertEqual(len(result), 0)
    
    def test_detect_with_none_value(self):
        """测试检测 None 值"""
        configs = [
            {
                'section': 'test',
                'key': 'none_value',
                'value': None
            }
        ]
        
        result = self.detector.detect(configs)
        
        # 验证没有检测到敏感信息
        self.assertEqual(len(result), 0)
    
    def test_detect_with_numeric_value(self):
        """测试检测数字类型的值"""
        configs = [
            {
                'section': 'test',
                'key': 'number',
                'value': 12345
            }
        ]
        
        result = self.detector.detect(configs)
        
        # 验证检测到敏感信息（数字会被转换为字符串）
        self.assertEqual(len(result), 1)
        self.assertIn('12345', result[0]['matches'])
    
    def test_detect_with_missing_section(self):
        """测试检测缺少 section 字段的配置"""
        configs = [
            {
                'key': 'qq',
                'value': '12345'
            }
        ]
        
        result = self.detector.detect(configs)
        
        # 验证检测到敏感信息，path 只包含 key
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['path'], 'qq')
    
    def test_detect_boundary_values(self):
        """测试边界值：5 位、6 位、10 位、11 位数字"""
        configs = [
            {'section': 'test', 'key': 'five', 'value': '12345'},      # 5 位：应检测
            {'section': 'test', 'key': 'six', 'value': '123456'},      # 6 位：应检测
            {'section': 'test', 'key': 'ten', 'value': '1234567890'},  # 10 位：应检测
            {'section': 'test', 'key': 'eleven', 'value': '12345678901'}, # 11 位：应检测
        ]
        
        result = self.detector.detect(configs)
        
        # 验证所有边界值都被检测到
        self.assertEqual(len(result), 4)
    
    def test_detect_with_special_characters(self):
        """测试包含特殊字符的文本"""
        configs = [
            {
                'section': 'test',
                'key': 'text',
                'value': 'QQ号码：12345，请添加！'
            }
        ]
        
        result = self.detector.detect(configs)
        
        # 验证检测到敏感信息
        self.assertEqual(len(result), 1)
        self.assertIn('12345', result[0]['matches'])
    
    def test_detect_with_word_boundaries(self):
        """测试单词边界检测"""
        configs = [
            {
                'section': 'test',
                'key': 'text',
                'value': 'abc12345def'  # 数字前后有字母，不应检测
            }
        ]
        
        result = self.detector.detect(configs)
        
        # 验证没有检测到敏感信息（因为使用了 \b 单词边界）
        self.assertEqual(len(result), 0)
    
    def test_detect_with_spaces_around_numbers(self):
        """测试数字周围有空格的情况"""
        configs = [
            {
                'section': 'test',
                'key': 'text',
                'value': '请联系 12345 获取信息'
            }
        ]
        
        result = self.detector.detect(configs)
        
        # 验证检测到敏感信息
        self.assertEqual(len(result), 1)
        self.assertIn('12345', result[0]['matches'])

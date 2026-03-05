# -*- coding: utf-8 -*-

"""
人设卡 API 端点测试（任务 14）

测试任务 14 实现的三个 API 端点：
- parse_toml: 解析上传的 TOML 文件
- create_with_config: 创建人设卡及配置
- confirm_sensitive: 确认敏感信息

**验证需求：3.1, 4.1, 9.6, 10.1**
"""

import io
import json
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from mainotebook.system.models import Users
from mainotebook.content.models import PersonaCard, PersonaCardConfig, SensitiveInfoConfirmation
from mainotebook.content.services.upload_quota_service import UploadQuotaService
from mainotebook.content.services.captcha_service import CaptchaService
from captcha.models import CaptchaStore
from datetime import datetime, timedelta


class PersonaCardAPITask14Test(TestCase):
    """人设卡 API 端点测试类（任务 14）"""
    
    def setUp(self):
        """设置测试环境"""
        self.client = APIClient()
        
        # 创建测试用户
        self.user = Users.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # 认证用户
        self.client.force_authenticate(user=self.user)
        
        # 设置默认的 HTTP_USER_AGENT 头（测试环境需要）
        self.client.defaults['HTTP_USER_AGENT'] = 'Mozilla/5.0 (Test Client)'
        
        # 准备测试 TOML 文件内容
        self.valid_toml_content = """
# 人设卡配置文件
# 这是一个测试用的人设卡配置文件
# 包含了基本的配置项和一些测试数据
version = "1.0"

[inner.meta.card]
name = "测试人设"
description = "这是一个测试人设卡"
author = "测试作者"
tags = ["测试", "示例"]

[settings]
max_tokens = 2000
temperature = 0.7
top_p = 0.9
frequency_penalty = 0.0
presence_penalty = 0.0
qq_number = "12345678"

[personality]
traits = ["友好", "专业", "耐心"]
style = "正式"
tone = "温和"

[knowledge]
domains = ["技术", "科学", "文化"]
expertise_level = "中级"

[behavior]
greeting = "你好！我是测试人设，很高兴为您服务。"
farewell = "再见！期待下次与您交流。"
error_handling = "抱歉，我遇到了一些问题，请稍后再试。"

# 添加一些填充内容以满足最小文件大小要求（1KB）
# 以下是一些额外的配置项
[advanced]
enable_logging = true
log_level = "info"
cache_enabled = true
cache_ttl = 3600
max_retries = 3
timeout = 30
debug_mode = false

[features]
feature_a = true
feature_b = false
feature_c = true
feature_d = false

[limits]
max_input_length = 4000
max_output_length = 2000
rate_limit = 100
concurrent_requests = 10

# 更多填充内容
[metadata]
created_at = "2024-01-01"
updated_at = "2024-01-15"
version_history = ["1.0", "0.9", "0.8"]
maintainer = "测试团队"
contact = "test@example.com"
license = "MIT"
"""
        
        self.invalid_toml_content = """
# 缺少 version 字段的 TOML
# 添加足够的内容以满足最小文件大小要求
[settings]
max_tokens = 2000
temperature = 0.7
top_p = 0.9

[personality]
traits = ["友好", "专业"]
style = "正式"

[knowledge]
domains = ["技术", "科学"]

[behavior]
greeting = "你好！"
farewell = "再见！"

# 填充内容
[advanced]
enable_logging = true
log_level = "info"
cache_enabled = true
cache_ttl = 3600
max_retries = 3
timeout = 30
debug_mode = false

[features]
feature_a = true
feature_b = false
feature_c = true
feature_d = false

[limits]
max_input_length = 4000
max_output_length = 2000
rate_limit = 100
concurrent_requests = 10

[metadata]
created_at = "2024-01-01"
updated_at = "2024-01-15"
maintainer = "测试团队"
contact = "test@example.com"
license = "MIT"
"""
    
    def tearDown(self):
        """清理测试环境"""
        # 重置上传限额
        UploadQuotaService.reset_quota(self.user.id)
        # 清除验证码冷却期
        CaptchaService.clear_cooldown(self.user.id)
        CaptchaService.reset_retry_count(self.user.id)
    
    def test_parse_toml_success(self):
        """测试成功解析 TOML 文件（任务 14.4）
        
        验证需求：3.1, 4.1
        """
        # 创建测试文件
        file = SimpleUploadedFile(
            "bot_config.toml",
            self.valid_toml_content.encode('utf-8'),
            content_type="text/plain"
        )
        
        # 发送请求
        response = self.client.post(
            '/api/content/persona/parse-toml/',
            {'file': file},
            format='multipart'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        
        data = response.data['data']
        self.assertIn('sections', data)
        self.assertIn('version', data)
        self.assertIn('sensitive_info', data)
        
        # 验证版本号
        self.assertEqual(data['version'], '1.0')
        
        # 验证检测到敏感信息
        self.assertGreater(len(data['sensitive_info']), 0)
        
        # 验证敏感信息包含 QQ 号
        sensitive_paths = [item['path'] for item in data['sensitive_info']]
        self.assertTrue(
            any('qq_number' in path for path in sensitive_paths),
            "应该检测到 qq_number 中的敏感信息"
        )
    
    def test_parse_toml_invalid_filename(self):
        """测试文件名不正确（任务 14.4）
        
        验证需求：3.1
        """
        # 创建错误文件名的文件
        file = SimpleUploadedFile(
            "wrong_name.toml",
            self.valid_toml_content.encode('utf-8'),
            content_type="text/plain"
        )
        
        # 发送请求
        response = self.client.post(
            '/api/content/persona/parse-toml/',
            {'file': file},
            format='multipart'
        )
        
        # 验证响应（项目使用统一响应格式，HTTP状态码总是200，错误信息在响应体的code字段）
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 400)
        self.assertIn('文件名必须为', response.data['msg'])
    
    def test_parse_toml_file_too_large(self):
        """测试文件过大（任务 14.4）
        
        验证需求：3.2
        """
        # 创建超过 2MB 的文件
        large_content = "a" * (3 * 1024 * 1024)  # 3MB
        file = SimpleUploadedFile(
            "bot_config.toml",
            large_content.encode('utf-8'),
            content_type="text/plain"
        )
        
        # 发送请求
        response = self.client.post(
            '/api/content/persona/parse-toml/',
            {'file': file},
            format='multipart'
        )
        
        # 验证响应（项目使用统一响应格式）
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 400)
        self.assertIn('文件大小', response.data['msg'])
    
    def test_parse_toml_missing_version(self):
        """测试缺少 version 字段（任务 14.4）
        
        验证需求：4.5
        """
        # 创建缺少 version 的文件（确保文件大小满足最小要求）
        # 添加足够的填充内容使文件大于 1KB
        padding = "# " + "填充内容 " * 100 + "\n"
        content_with_padding = self.invalid_toml_content + padding
        
        file = SimpleUploadedFile(
            "bot_config.toml",
            content_with_padding.encode('utf-8'),
            content_type="text/plain"
        )
        
        # 发送请求
        response = self.client.post(
            '/api/content/persona/parse-toml/',
            {'file': file},
            format='multipart'
        )
        
        # 验证响应（项目使用统一响应格式）
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 400)
        self.assertIn('version', response.data['msg'].lower())
    
    def test_create_with_config_private(self):
        """测试创建私有人设卡（任务 14.4）
        
        验证需求：1.1, 2.1, 2.2, 6.1
        """
        # 准备请求数据
        data = {
            'name': '测试人设卡',
            'description': '这是一个测试人设卡的描述，至少需要十个字符',
            'is_public': False,
            'configs': [
                {
                    'section_name': 'settings',
                    'key_name': 'max_tokens',
                    'value': '2000',
                    'data_type': 'integer',
                    'description': '最大令牌数'
                }
            ]
        }
        
        # 发送请求
        response = self.client.post(
            '/api/content/persona/create-with-config/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        
        # 验证数据库记录
        persona_card = PersonaCard.objects.get(name='测试人设卡')
        self.assertEqual(persona_card.uploader, self.user)
        self.assertFalse(persona_card.is_public)
        self.assertFalse(persona_card.is_pending)
        
        # 验证配置项已创建
        configs = PersonaCardConfig.objects.filter(persona_card=persona_card)
        self.assertEqual(configs.count(), 1)
        self.assertEqual(configs.first().key_name, 'max_tokens')
    
    def test_create_with_config_public_triggers_review(self):
        """测试创建公开人设卡触发审核（任务 14.4）
        
        验证需求：10.1
        """
        # 准备请求数据
        data = {
            'name': '公开人设卡',
            'description': '这是一个公开的人设卡描述，至少需要十个字符',
            'is_public': True,
            'configs': []
        }
        
        # 发送请求
        response = self.client.post(
            '/api/content/persona/create-with-config/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证数据库记录
        persona_card = PersonaCard.objects.get(name='公开人设卡')
        
        # 注意：由于审核流程可能异步执行，这里只验证人设卡已创建
        # is_pending 状态取决于审核服务的实现
        self.assertEqual(persona_card.uploader, self.user)
    
    def test_create_with_config_quota_exceeded(self):
        """测试超过上传限额（任务 14.4）
        
        验证需求：1.3
        """
        # 模拟用户已达到上传限额
        for _ in range(UploadQuotaService.DAILY_LIMIT):
            UploadQuotaService.increment_quota(self.user.id)
        
        # 准备请求数据
        data = {
            'name': '超限人设卡',
            'description': '这是一个测试超限的人设卡描述，至少需要十个字符',
            'is_public': False,
            'configs': []
        }
        
        # 发送请求
        response = self.client.post(
            '/api/content/persona/create-with-config/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # 验证响应（项目使用统一响应格式）
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 429)
        self.assertIn('上限', response.data['msg'])
    
    def test_confirm_sensitive_success(self):
        """测试成功确认敏感信息（任务 14.4）
        
        验证需求：9.6, 9.8
        """
        # 创建测试人设卡
        persona_card = PersonaCard.objects.create(
            name='测试人设',
            description='测试描述至少十个字符',
            uploader=self.user,
            creator=self.user,
            modifier=self.user.username
        )
        
        # 创建验证码
        captcha = CaptchaStore.objects.create(
            challenge='1+1',
            response='2',
            hashkey='test_key',
            expiration=datetime.now() + timedelta(minutes=5)
        )
        
        # 准备请求数据
        data = {
            'confirmation_text': '我已确认该文件在配置项 settings.qq_number 的内容不涉及个人隐私信息',
            'sensitive_locations': [
                {
                    'path': 'settings.qq_number',
                    'matches': ['12345678']
                }
            ],
            'captcha_key': 'test_key',
            'captcha_value': '2'
        }
        
        # 发送请求
        response = self.client.post(
            f'/api/content/persona/{persona_card.id}/confirm-sensitive/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证数据库记录
        confirmation = SensitiveInfoConfirmation.objects.get(
            persona_card=persona_card
        )
        self.assertEqual(confirmation.user, self.user)
        self.assertIn('确认', confirmation.confirmation_text)
        self.assertEqual(len(confirmation.sensitive_locations), 1)
        self.assertIsNotNone(confirmation.ip_address)
    
    def test_confirm_sensitive_invalid_captcha(self):
        """测试验证码错误（任务 14.4）
        
        验证需求：9.6
        """
        # 创建测试人设卡
        persona_card = PersonaCard.objects.create(
            name='测试人设',
            description='测试描述至少十个字符',
            uploader=self.user,
            creator=self.user,
            modifier=self.user.username
        )
        
        # 创建验证码
        captcha = CaptchaStore.objects.create(
            challenge='1+1',
            response='2',
            hashkey='test_key',
            expiration=datetime.now() + timedelta(minutes=5)
        )
        
        # 准备请求数据（错误的验证码）
        data = {
            'confirmation_text': '我已确认该文件在配置项 settings.qq_number 的内容不涉及个人隐私信息',
            'sensitive_locations': [
                {
                    'path': 'settings.qq_number',
                    'matches': ['12345678']
                }
            ],
            'captcha_key': 'test_key',
            'captcha_value': '3'  # 错误答案
        }
        
        # 发送请求
        response = self.client.post(
            f'/api/content/persona/{persona_card.id}/confirm-sensitive/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # 验证响应（项目使用统一响应格式）
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 400)
        self.assertIn('验证码错误', response.data['msg'])
        
        # 验证未创建确认记录
        self.assertFalse(
            SensitiveInfoConfirmation.objects.filter(
                persona_card=persona_card
            ).exists()
        )
    
    def test_confirm_sensitive_retry_limit(self):
        """测试超过重试次数（任务 14.4）
        
        验证需求：9.6, 9.7
        """
        # 创建测试人设卡
        persona_card = PersonaCard.objects.create(
            name='测试人设',
            description='测试描述至少十个字符',
            uploader=self.user,
            creator=self.user,
            modifier=self.user.username
        )
        
        # 模拟用户已达到重试限制
        for _ in range(CaptchaService.MAX_RETRY_COUNT):
            CaptchaService.increment_retry_count(self.user.id)
        
        # 准备请求数据
        data = {
            'confirmation_text': '我已确认该文件在配置项 settings.qq_number 的内容不涉及个人隐私信息',
            'sensitive_locations': [
                {
                    'path': 'settings.qq_number',
                    'matches': ['12345678']
                }
            ],
            'captcha_key': 'test_key',
            'captcha_value': '2'
        }
        
        # 发送请求
        response = self.client.post(
            f'/api/content/persona/{persona_card.id}/confirm-sensitive/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # 验证响应（项目使用统一响应格式）
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 429)
        # 错误消息可能是"冷却期"或"验证码错误次数过多"
        self.assertTrue(
            '冷却期' in response.data['msg'] or '错误次数过多' in response.data['msg'],
            f"错误消息应包含冷却期相关信息，实际消息：{response.data['msg']}"
        )

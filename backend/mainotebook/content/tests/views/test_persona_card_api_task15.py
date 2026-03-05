# -*- coding: utf-8 -*-

"""
人设卡 API 端点测试（任务 15）

测试任务 15 实现的四个 API 端点：
- get_config: 获取配置项
- update_config: 更新配置项
- export_toml: 导出 TOML 文件
- download: 下载人设卡

**验证需求：7.3, 12.3, 12.4, 13.1, 13.2**
"""

import json
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from mainotebook.system.models import Users
from mainotebook.content.models import PersonaCard, PersonaCardConfig
from mainotebook.content.services.persona_card_config_service import PersonaCardConfigService


class PersonaCardAPITask15Test(TestCase):
    """人设卡 API 端点测试类（任务 15）"""
    
    def setUp(self):
        """设置测试环境"""
        self.client = APIClient()
        
        # 创建测试用户
        self.user = Users.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # 创建另一个用户用于权限测试
        self.other_user = Users.objects.create_user(
            username='otheruser',
            password='testpass123',
            email='other@example.com'
        )
        
        # 认证用户
        self.client.force_authenticate(user=self.user)
        
        # 设置默认的 HTTP_USER_AGENT 头
        self.client.defaults['HTTP_USER_AGENT'] = 'Mozilla/5.0 (Test Client)'
        
        # 创建测试人设卡
        self.persona_card = PersonaCard.objects.create(
            name='测试人设卡',
            description='这是一个测试人设卡的描述',
            uploader=self.user,
            is_public=False,
            is_pending=False,
            creator=self.user,
            modifier=self.user.username
        )
        
        # 创建测试配置项
        self.test_configs = [
            {
                'section_name': 'settings',
                'key_name': 'max_tokens',
                'value': '2000',
                'data_type': 'integer',
                'description': '最大令牌数'
            },
            {
                'section_name': 'settings',
                'key_name': 'temperature',
                'value': '0.7',
                'data_type': 'float',
                'description': '温度参数'
            },
            {
                'section_name': 'personality',
                'key_name': 'traits',
                'value': '["友好", "专业"]',
                'data_type': 'array',
                'description': '性格特征'
            }
        ]
        
        for config_data in self.test_configs:
            PersonaCardConfig.objects.create(
                persona_card=self.persona_card,
                creator=self.user,
                modifier=self.user.username,
                **config_data
            )
    
    def test_get_config_success(self):
        """测试成功获取配置项（任务 15.5）
        
        验证需求：7.1, 7.2
        """
        # 发送请求
        response = self.client.get(
            f'/api/content/persona/{self.persona_card.id}/config/'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        
        data = response.data['data']
        self.assertIn('sections', data)
        
        # 验证配置块分组
        sections = data['sections']
        self.assertGreater(len(sections), 0)
        
        # 验证 settings 块
        settings_section = next(
            (s for s in sections if s['name'] == 'settings'),
            None
        )
        self.assertIsNotNone(settings_section)
        self.assertEqual(len(settings_section['items']), 2)
        
        # 验证配置项内容
        max_tokens_item = next(
            (item for item in settings_section['items'] if item['key'] == 'max_tokens'),
            None
        )
        self.assertIsNotNone(max_tokens_item)
        self.assertEqual(max_tokens_item['value'], 2000)
        self.assertEqual(max_tokens_item['type'], 'integer')
    
    def test_get_config_permission_denied(self):
        """测试获取配置项权限验证（任务 15.5）
        
        验证需求：7.1
        """
        # 切换到其他用户
        self.client.force_authenticate(user=self.other_user)
        
        # 发送请求
        response = self.client.get(
            f'/api/content/persona/{self.persona_card.id}/config/'
        )
        
        # 验证响应（项目使用统一响应格式）
        # 由于 get_queryset 已经过滤，会返回 404
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 验证返回的是错误响应（code 不是 2000）
        self.assertNotEqual(response.data['code'], 2000)
    
    def test_update_config_success(self):
        """测试成功更新配置项（任务 15.5）
        
        验证需求：7.3
        """
        # 准备更新数据
        data = {
            'updates': [
                {
                    'section': 'settings',
                    'key': 'max_tokens',
                    'value': 3000,
                    'comment': '更新后的最大令牌数'
                },
                {
                    'section': 'settings',
                    'key': 'temperature',
                    'value': 0.8
                }
            ]
        }
        
        # 发送请求
        response = self.client.put(
            f'/api/content/persona/{self.persona_card.id}/config/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        
        # 验证数据库更新
        config = PersonaCardConfig.objects.get(
            persona_card=self.persona_card,
            section_name='settings',
            key_name='max_tokens'
        )
        self.assertEqual(config.value, '3000')
        self.assertEqual(config.description, '更新后的最大令牌数')
    
    def test_update_config_delete_section(self):
        """测试删除配置块（任务 15.5）
        
        验证需求：7.4
        """
        # 准备更新数据
        data = {
            'deleted_sections': ['personality']
        }
        
        # 发送请求
        response = self.client.put(
            f'/api/content/persona/{self.persona_card.id}/config/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证配置块被标记为删除
        deleted_configs = PersonaCardConfig.objects.filter(
            persona_card=self.persona_card,
            section_name='personality',
            is_deleted=True
        )
        self.assertGreater(deleted_configs.count(), 0)
    
    def test_update_config_edit_permission_denied(self):
        """测试更新配置项编辑权限限制（任务 15.5）
        
        验证需求：12.3, 12.4
        """
        # 测试非上传者无法编辑
        self.client.force_authenticate(user=self.other_user)
        
        data = {
            'updates': [
                {
                    'section': 'settings',
                    'key': 'max_tokens',
                    'value': 3000
                }
            ]
        }
        
        response = self.client.put(
            f'/api/content/persona/{self.persona_card.id}/config/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # 验证响应
        # 由于 get_queryset 已经过滤，会返回 404
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 验证返回的是错误响应（code 不是 2000）
        self.assertNotEqual(response.data['code'], 2000)
    
    def test_update_config_pending_card_denied(self):
        """测试审核中的人设卡不能编辑（任务 15.5）
        
        验证需求：12.4
        """
        # 将人设卡设置为审核中
        self.persona_card.is_pending = True
        self.persona_card.save()
        
        data = {
            'updates': [
                {
                    'section': 'settings',
                    'key': 'max_tokens',
                    'value': 3000
                }
            ]
        }
        
        response = self.client.put(
            f'/api/content/persona/{self.persona_card.id}/config/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 403)
        self.assertIn('审核', response.data['msg'])
    
    def test_update_config_public_approved_card_denied(self):
        """测试已通过审核的公开人设卡不能编辑（任务 15.5）
        
        验证需求：12.4
        """
        # 将人设卡设置为公开且已通过审核
        self.persona_card.is_public = True
        self.persona_card.is_pending = False
        self.persona_card.save()
        
        data = {
            'updates': [
                {
                    'section': 'settings',
                    'key': 'max_tokens',
                    'value': 3000
                }
            ]
        }
        
        response = self.client.put(
            f'/api/content/persona/{self.persona_card.id}/config/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 403)
        self.assertIn('公开', response.data['msg'])
    
    def test_export_toml_success(self):
        """测试成功导出 TOML（任务 15.5）
        
        验证需求：5.3, 5.4, 5.5, 5.6
        """
        # 发送请求
        response = self.client.post(
            f'/api/content/persona/{self.persona_card.id}/export-toml/'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        
        data = response.data['data']
        self.assertIn('content', data)
        self.assertIn('deleted_sections', data)
        
        # 验证 TOML 内容
        toml_content = data['content']
        self.assertIn('[settings]', toml_content)
        self.assertIn('max_tokens', toml_content)
        self.assertIn('2000', toml_content)
        
        # 验证被删除块列表
        self.assertIsInstance(data['deleted_sections'], list)
    
    def test_export_toml_with_deleted_sections(self):
        """测试导出包含被删除块的 TOML（任务 15.5）
        
        验证需求：5.6
        """
        # 标记一个配置块为删除
        PersonaCardConfig.objects.filter(
            persona_card=self.persona_card,
            section_name='personality'
        ).update(is_deleted=True)
        
        # 发送请求
        response = self.client.post(
            f'/api/content/persona/{self.persona_card.id}/export-toml/'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data['data']
        
        # 验证被删除块列表包含 personality
        self.assertIn('personality', data['deleted_sections'])
        
        # 验证 TOML 内容包含被删除块的注释
        toml_content = data['content']
        self.assertIn('[personality]', toml_content)
        self.assertIn('已被作者删除', toml_content)
    
    def test_download_success(self):
        """测试成功下载人设卡（任务 15.5）
        
        验证需求：13.1, 13.2, 13.4, 13.8
        """
        # 将人设卡设置为公开且已通过审核
        self.persona_card.is_public = True
        self.persona_card.is_pending = False
        self.persona_card.downloads = 0
        self.persona_card.save()
        
        # 发送请求
        response = self.client.get(
            f'/api/content/persona/{self.persona_card.id}/download/'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/toml')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('bot_config.toml', response['Content-Disposition'])
        
        # 验证响应内容
        content = response.content.decode('utf-8')
        self.assertIn('[settings]', content)
        self.assertIn('max_tokens', content)
        
        # 验证下载计数增加
        self.persona_card.refresh_from_db()
        self.assertEqual(self.persona_card.downloads, 1)
    
    def test_download_permission_denied_not_authenticated(self):
        """测试未登录用户无法下载（任务 15.5）
        
        验证需求：13.1
        """
        # 将人设卡设置为公开且已通过审核
        self.persona_card.is_public = True
        self.persona_card.is_pending = False
        self.persona_card.save()
        
        # 取消认证
        self.client.force_authenticate(user=None)
        
        # 发送请求
        response = self.client.get(
            f'/api/content/persona/{self.persona_card.id}/download/'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 401)
        self.assertIn('登录', response.data['msg'])
    
    def test_download_permission_denied_not_public(self):
        """测试私有人设卡无法下载（任务 15.5）
        
        验证需求：13.1
        """
        # 人设卡保持私有状态
        self.persona_card.is_public = False
        self.persona_card.save()
        
        # 发送请求
        response = self.client.get(
            f'/api/content/persona/{self.persona_card.id}/download/'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 403)
        self.assertIn('未公开', response.data['msg'])
    
    def test_download_permission_denied_pending(self):
        """测试审核中的人设卡无法下载（任务 15.5）
        
        验证需求：13.1
        """
        # 将人设卡设置为公开但审核中
        self.persona_card.is_public = True
        self.persona_card.is_pending = True
        self.persona_card.save()
        
        # 发送请求
        response = self.client.get(
            f'/api/content/persona/{self.persona_card.id}/download/'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 403)
        self.assertIn('审核', response.data['msg'])
    
    def test_download_increments_count(self):
        """测试下载增加下载计数（任务 15.5）
        
        验证需求：13.2
        """
        # 将人设卡设置为公开且已通过审核
        self.persona_card.is_public = True
        self.persona_card.is_pending = False
        self.persona_card.downloads = 5
        self.persona_card.save()
        
        # 发送请求
        response = self.client.get(
            f'/api/content/persona/{self.persona_card.id}/download/'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证下载计数增加
        self.persona_card.refresh_from_db()
        self.assertEqual(self.persona_card.downloads, 6)
        
        # 再次下载
        response = self.client.get(
            f'/api/content/persona/{self.persona_card.id}/download/'
        )
        
        # 验证下载计数再次增加
        self.persona_card.refresh_from_db()
        self.assertEqual(self.persona_card.downloads, 7)

# -*- coding: utf-8 -*-

"""
人设卡序列化器测试

测试人设卡序列化器的数据验证、TOML 文件验证、序列化功能。

验证需求：2.1, 2.12, 10.3
"""

from django.test import TestCase
from rest_framework.test import APIRequestFactory
from mainotebook.system.models import Users
from mainotebook.content.models import PersonaCard, PersonaCardFile, StarRecord
from mainotebook.content.serializers.persona_card import (
    PersonaCardSerializer,
    PersonaCardCreateSerializer,
    PersonaCardUpdateSerializer,
    PersonaCardFileSerializer,
)


class TestPersonaCardFileSerializer(TestCase):
    """测试人设卡文件序列化器"""
    
    def setUp(self):
        """测试前准备"""
        self.user = Users.objects.create(
            username="testuser",
            name="测试用户",
            email="test@example.com"
        )
        self.persona_card = PersonaCard.objects.create(
            name="测试人设卡",
            description="测试描述",
            uploader=self.user
        )
    
    def tearDown(self):
        """测试后清理"""
        PersonaCardFile.objects.all().delete()
        PersonaCard.objects.all().delete()
        Users.objects.all().delete()
    
    def test_serialize_file(self):
        """测试文件序列化"""
        file = PersonaCardFile.objects.create(
            persona_card=self.persona_card,
            file_name="test_file.txt",
            original_name="原始文件.txt",
            file_path="/path/to/file.txt",
            file_type="text/plain",
            file_size=1024
        )
        
        serializer = PersonaCardFileSerializer(file)
        data = serializer.data
        
        # 验证字段存在和值
        self.assertIn('id', data)
        self.assertEqual(data['file_name'], "test_file.txt")
        self.assertEqual(data['original_name'], "原始文件.txt")
        self.assertEqual(data['file_type'], "text/plain")
        self.assertEqual(data['file_size'], 1024)
    
    def test_read_only_fields(self):
        """测试只读字段"""
        serializer = PersonaCardFileSerializer()
        self.assertIn('id', serializer.Meta.read_only_fields)
        self.assertIn('create_datetime', serializer.Meta.read_only_fields)


class TestPersonaCardSerializer(TestCase):
    """测试人设卡列表序列化器"""
    
    def setUp(self):
        """测试前准备"""
        self.factory = APIRequestFactory()
        self.user = Users.objects.create(
            username="testuser",
            name="测试用户",
            email="test@example.com",
            avatar="avatar.jpg"
        )
    
    def tearDown(self):
        """测试后清理"""
        PersonaCard.objects.all().delete()
        Users.objects.all().delete()
    
    def test_serialize_persona_card(self):
        """测试人设卡序列化（需求 10.3）"""
        persona_card = PersonaCard.objects.create(
            name="测试人设卡",
            description="测试描述",
            uploader=self.user,
            tags="AI,助手",
            version="1.0"
        )
        
        request = self.factory.get('/')
        request.user = self.user
        
        serializer = PersonaCardSerializer(persona_card, context={'request': request})
        data = serializer.data
        
        # 验证基本字段
        self.assertEqual(data['name'], "测试人设卡")
        self.assertEqual(data['description'], "测试描述")
        self.assertEqual(data['uploader_name'], "测试用户")
        self.assertEqual(data['uploader_avatar'], "avatar.jpg")
        self.assertEqual(data['tags'], "AI,助手")
        self.assertEqual(data['version'], "1.0")
        
        # 验证关联字段
        self.assertIn('files', data)
        self.assertIn('is_starred', data)
        self.assertIn('has_valid_toml', data)
    
    def test_get_files(self):
        """测试获取文件列表"""
        persona_card = PersonaCard.objects.create(
            name="测试人设卡",
            description="测试描述",
            uploader=self.user
        )
        
        # 创建测试文件
        PersonaCardFile.objects.create(
            persona_card=persona_card,
            file_name="file1.txt",
            original_name="文件1.txt",
            file_path="/path/to/file1.txt",
            file_type="text/plain",
            file_size=1024
        )
        PersonaCardFile.objects.create(
            persona_card=persona_card,
            file_name="bot_config.toml",
            original_name="bot_config.toml",
            file_path="/path/to/bot_config.toml",
            file_type="application/toml",
            file_size=512
        )
        
        request = self.factory.get('/')
        request.user = self.user
        
        serializer = PersonaCardSerializer(persona_card, context={'request': request})
        data = serializer.data
        
        # 验证文件列表
        self.assertEqual(len(data['files']), 2)
        file_names = [f['original_name'] for f in data['files']]
        self.assertIn('文件1.txt', file_names)
        self.assertIn('bot_config.toml', file_names)
    
    def test_get_is_starred_authenticated(self):
        """测试已认证用户的收藏状态"""
        persona_card = PersonaCard.objects.create(
            name="测试人设卡",
            description="测试描述",
            uploader=self.user
        )
        
        # 创建收藏记录
        StarRecord.objects.create(
            user=self.user,
            target_id=str(persona_card.id),
            target_type='persona'
        )
        
        request = self.factory.get('/')
        request.user = self.user
        
        serializer = PersonaCardSerializer(persona_card, context={'request': request})
        data = serializer.data
        
        # 验证收藏状态
        self.assertTrue(data['is_starred'])
    
    def test_get_is_starred_not_starred(self):
        """测试未收藏的状态"""
        persona_card = PersonaCard.objects.create(
            name="测试人设卡",
            description="测试描述",
            uploader=self.user
        )
        
        request = self.factory.get('/')
        request.user = self.user
        
        serializer = PersonaCardSerializer(persona_card, context={'request': request})
        data = serializer.data
        
        # 验证未收藏状态
        self.assertFalse(data['is_starred'])
    
    def test_get_has_valid_toml_with_one_file(self):
        """测试包含唯一 TOML 文件的情况（需求 2.12）"""
        persona_card = PersonaCard.objects.create(
            name="测试人设卡",
            description="测试描述",
            uploader=self.user
        )
        
        # 创建唯一的 bot_config.toml 文件
        PersonaCardFile.objects.create(
            persona_card=persona_card,
            file_name="bot_config.toml",
            original_name="bot_config.toml",
            file_path="/path/to/bot_config.toml",
            file_type="application/toml",
            file_size=512
        )
        
        request = self.factory.get('/')
        request.user = self.user
        
        serializer = PersonaCardSerializer(persona_card, context={'request': request})
        data = serializer.data
        
        # 验证 TOML 文件有效性
        self.assertTrue(data['has_valid_toml'])
    
    def test_get_has_valid_toml_with_no_file(self):
        """测试不包含 TOML 文件的情况（需求 2.12）"""
        persona_card = PersonaCard.objects.create(
            name="测试人设卡",
            description="测试描述",
            uploader=self.user
        )
        
        request = self.factory.get('/')
        request.user = self.user
        
        serializer = PersonaCardSerializer(persona_card, context={'request': request})
        data = serializer.data
        
        # 验证 TOML 文件无效
        self.assertFalse(data['has_valid_toml'])
    
    def test_get_has_valid_toml_with_multiple_files(self):
        """测试包含多个 TOML 文件的情况（需求 2.12）"""
        persona_card = PersonaCard.objects.create(
            name="测试人设卡",
            description="测试描述",
            uploader=self.user
        )
        
        # 创建多个 bot_config.toml 文件
        PersonaCardFile.objects.create(
            persona_card=persona_card,
            file_name="bot_config_1.toml",
            original_name="bot_config.toml",
            file_path="/path/to/bot_config_1.toml",
            file_type="application/toml",
            file_size=512
        )
        PersonaCardFile.objects.create(
            persona_card=persona_card,
            file_name="bot_config_2.toml",
            original_name="bot_config.toml",
            file_path="/path/to/bot_config_2.toml",
            file_type="application/toml",
            file_size=512
        )
        
        request = self.factory.get('/')
        request.user = self.user
        
        serializer = PersonaCardSerializer(persona_card, context={'request': request})
        data = serializer.data
        
        # 验证 TOML 文件无效（多个文件）
        self.assertFalse(data['has_valid_toml'])


class TestPersonaCardCreateSerializer(TestCase):
    """测试人设卡创建序列化器"""
    
    def setUp(self):
        """测试前准备"""
        self.factory = APIRequestFactory()
        self.user = Users.objects.create(
            username="testuser",
            name="测试用户",
            email="test@example.com"
        )
    
    def tearDown(self):
        """测试后清理"""
        PersonaCard.objects.all().delete()
        Users.objects.all().delete()
    
    def test_create_with_valid_data(self):
        """测试使用有效数据创建人设卡（需求 2.1）"""
        request = self.factory.post('/')
        request.user = self.user
        
        data = {
            'name': '新人设卡',
            'description': '描述',
            'copyright_owner': '版权所有者',
            'content': '内容',
            'tags': 'AI,助手',
            'version': '1.0'
        }
        
        serializer = PersonaCardCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        persona_card = serializer.save()
        
        # 验证创建成功
        self.assertEqual(persona_card.name, '新人设卡')
        self.assertEqual(persona_card.description, '描述')
        self.assertEqual(persona_card.uploader, self.user)
        self.assertEqual(persona_card.copyright_owner, '版权所有者')
        self.assertEqual(persona_card.tags, 'AI,助手')
        self.assertEqual(persona_card.version, '1.0')
    
    def test_create_with_minimal_data(self):
        """测试使用最少必填字段创建人设卡（需求 2.1）"""
        request = self.factory.post('/')
        request.user = self.user
        
        data = {
            'name': '最小人设卡',
            'description': '最小描述'
        }
        
        serializer = PersonaCardCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        persona_card = serializer.save()
        
        # 验证创建成功
        self.assertEqual(persona_card.name, '最小人设卡')
        self.assertEqual(persona_card.uploader, self.user)
    
    def test_validate_name_uniqueness_success(self):
        """测试名称唯一性验证成功（需求 2.1）"""
        request = self.factory.post('/')
        request.user = self.user
        
        data = {'name': '唯一的人设卡', 'description': '描述'}
        
        serializer = PersonaCardCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
    
    def test_validate_name_uniqueness_failure(self):
        """测试名称唯一性验证失败（需求 2.1）"""
        # 创建已存在的人设卡
        PersonaCard.objects.create(
            name="重复的人设卡",
            description="描述",
            uploader=self.user
        )
        
        request = self.factory.post('/')
        request.user = self.user
        
        data = {'name': '重复的人设卡', 'description': '描述'}
        
        serializer = PersonaCardCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        # 验证失败
        self.assertFalse(serializer.is_valid())
        self.assertTrue('name' in serializer.errors or any('同名' in str(v) for v in serializer.errors.values()))
    
    def test_validate_name_uniqueness_different_user(self):
        """测试不同用户可以创建同名人设卡"""
        # 用户1创建人设卡
        user1 = self.user
        PersonaCard.objects.create(
            name="同名人设卡",
            description="描述",
            uploader=user1
        )
        
        # 用户2创建同名人设卡
        user2 = Users.objects.create(
            username="testuser2",
            name="测试用户2",
            email="test2@example.com"
        )
        
        request = self.factory.post('/')
        request.user = user2
        
        data = {'name': '同名人设卡', 'description': '描述'}
        
        serializer = PersonaCardCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        # 验证成功（不同用户可以创建同名人设卡）
        self.assertTrue(serializer.is_valid(), serializer.errors)
    
    def test_auto_set_uploader(self):
        """测试自动设置上传者（需求 2.1）"""
        request = self.factory.post('/')
        request.user = self.user
        
        data = {'name': '测试人设卡', 'description': '描述'}
        
        serializer = PersonaCardCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        persona_card = serializer.save()
        
        # 验证上传者自动设置
        self.assertEqual(persona_card.uploader, self.user)


class TestPersonaCardUpdateSerializer(TestCase):
    """测试人设卡更新序列化器"""
    
    def setUp(self):
        """测试前准备"""
        self.factory = APIRequestFactory()
        self.user = Users.objects.create(
            username="testuser",
            name="测试用户",
            email="test@example.com"
        )
        self.other_user = Users.objects.create(
            username="otheruser",
            name="其他用户",
            email="other@example.com"
        )
    
    def tearDown(self):
        """测试后清理"""
        PersonaCard.objects.all().delete()
        Users.objects.all().delete()
    
    def test_update_with_permission(self):
        """测试有权限时更新成功"""
        persona_card = PersonaCard.objects.create(
            name="原始名称",
            description="原始描述",
            uploader=self.user
        )
        
        request = self.factory.put('/')
        request.user = self.user
        
        data = {
            'name': '更新后的名称',
            'description': '更新后的描述',
            'tags': '新标签'
        }
        
        serializer = PersonaCardUpdateSerializer(
            persona_card,
            data=data,
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_persona_card = serializer.save()
        
        # 验证更新成功
        self.assertEqual(updated_persona_card.name, '更新后的名称')
        self.assertEqual(updated_persona_card.description, '更新后的描述')
        self.assertEqual(updated_persona_card.tags, '新标签')
    
    def test_update_without_permission(self):
        """测试无权限时更新失败"""
        persona_card = PersonaCard.objects.create(
            name="原始名称",
            description="原始描述",
            uploader=self.user
        )
        
        request = self.factory.put('/')
        request.user = self.other_user
        
        data = {'name': '更新后的名称', 'description': '更新后的描述'}
        
        serializer = PersonaCardUpdateSerializer(
            persona_card,
            data=data,
            context={'request': request}
        )
        
        # 验证失败
        self.assertFalse(serializer.is_valid())
        self.assertTrue(any('创建者' in str(v) for v in serializer.errors.values()))
    
    def test_validate_name_uniqueness_on_update(self):
        """测试更新时名称唯一性验证"""
        # 创建两个人设卡
        persona_card1 = PersonaCard.objects.create(
            name="人设卡1",
            description="描述1",
            uploader=self.user
        )
        PersonaCard.objects.create(
            name="人设卡2",
            description="描述2",
            uploader=self.user
        )
        
        request = self.factory.put('/')
        request.user = self.user
        
        # 尝试将人设卡1的名称改为人设卡2的名称
        data = {'name': '人设卡2', 'description': '描述1'}
        
        serializer = PersonaCardUpdateSerializer(
            persona_card1,
            data=data,
            context={'request': request}
        )
        
        # 验证失败
        self.assertFalse(serializer.is_valid())
        self.assertTrue('name' in serializer.errors or any('同名' in str(v) for v in serializer.errors.values()))
    
    def test_update_with_same_name(self):
        """测试更新时保持相同名称"""
        persona_card = PersonaCard.objects.create(
            name="原始名称",
            description="原始描述",
            uploader=self.user
        )
        
        request = self.factory.put('/')
        request.user = self.user
        
        # 保持相同名称，只更新描述
        data = {'name': '原始名称', 'description': '新描述'}
        
        serializer = PersonaCardUpdateSerializer(
            persona_card,
            data=data,
            context={'request': request}
        )
        
        # 验证成功（相同名称应该允许）
        self.assertTrue(serializer.is_valid(), serializer.errors)

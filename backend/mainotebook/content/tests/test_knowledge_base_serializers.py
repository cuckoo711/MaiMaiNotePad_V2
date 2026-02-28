# -*- coding: utf-8 -*-

"""
知识库序列化器测试

测试知识库序列化器的数据验证、序列化、反序列化功能。

验证需求：1.1, 1.12, 10.3
"""

from django.test import TestCase
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIRequestFactory
from mainotebook.system.models import Users
from mainotebook.content.models import KnowledgeBase, KnowledgeBaseFile, StarRecord
from mainotebook.content.serializers.knowledge_base import (
    KnowledgeBaseSerializer,
    KnowledgeBaseCreateSerializer,
    KnowledgeBaseUpdateSerializer,
    KnowledgeBaseFileSerializer,
)


class TestKnowledgeBaseFileSerializer(TestCase):
    """测试知识库文件序列化器"""
    
    def setUp(self):
        """测试前准备"""
        self.user = Users.objects.create(
            username="testuser",
            name="测试用户",
            email="test@example.com"
        )
        self.kb = KnowledgeBase.objects.create(
            name="测试知识库",
            description="测试描述",
            uploader=self.user
        )
    
    def tearDown(self):
        """测试后清理"""
        KnowledgeBaseFile.objects.all().delete()
        KnowledgeBase.objects.all().delete()
        Users.objects.all().delete()
    
    def test_serialize_file(self):
        """测试文件序列化"""
        file = KnowledgeBaseFile.objects.create(
            knowledge_base=self.kb,
            file_name="test_file.txt",
            original_name="原始文件.txt",
            file_path="/path/to/file.txt",
            file_type="text/plain",
            file_size=1024
        )
        
        serializer = KnowledgeBaseFileSerializer(file)
        data = serializer.data
        
        # 验证字段存在和值
        self.assertIn('id', data)
        self.assertEqual(data['file_name'], "test_file.txt")
        self.assertEqual(data['original_name'], "原始文件.txt")
    
    def test_read_only_fields(self):
        """测试只读字段"""
        serializer = KnowledgeBaseFileSerializer()
        self.assertIn('id', serializer.Meta.read_only_fields)


class TestKnowledgeBaseSerializer(TestCase):
    """测试知识库列表序列化器"""
    
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
        KnowledgeBase.objects.all().delete()
        Users.objects.all().delete()
    
    def test_serialize_knowledge_base(self):
        """测试知识库序列化（需求 10.3）"""
        kb = KnowledgeBase.objects.create(
            name="测试知识库",
            description="测试描述",
            uploader=self.user,
            tags="Python,Django",
            version="1.0"
        )
        
        request = self.factory.get('/')
        request.user = self.user
        
        serializer = KnowledgeBaseSerializer(kb, context={'request': request})
        data = serializer.data
        
        self.assertEqual(data['name'], "测试知识库")
        self.assertEqual(data['uploader_name'], "测试用户")
        self.assertIn('files', data)


class TestKnowledgeBaseCreateSerializer(TestCase):
    """测试知识库创建序列化器"""
    
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
        KnowledgeBase.objects.all().delete()
        Users.objects.all().delete()
    
    def test_create_with_valid_data(self):
        """测试使用有效数据创建知识库（需求 1.1）"""
        request = self.factory.post('/')
        request.user = self.user
        
        data = {'name': '新知识库', 'description': '描述'}
        
        serializer = KnowledgeBaseCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        kb = serializer.save()
        
        self.assertEqual(kb.name, '新知识库')
        self.assertEqual(kb.uploader, self.user)
    
    def test_validate_name_uniqueness_failure(self):
        """测试名称唯一性验证失败（需求 1.12）"""
        KnowledgeBase.objects.create(
            name="重复的知识库",
            description="描述",
            uploader=self.user
        )
        
        request = self.factory.post('/')
        request.user = self.user
        
        data = {'name': '重复的知识库', 'description': '描述'}
        
        serializer = KnowledgeBaseCreateSerializer(
            data=data,
            context={'request': request}
        )
        
        self.assertFalse(serializer.is_valid())
        # 错误可能在 'name' 或中文字段名中
        self.assertTrue('name' in serializer.errors or any('同名' in str(v) for v in serializer.errors.values()))


class TestKnowledgeBaseUpdateSerializer(TestCase):
    """测试知识库更新序列化器"""
    
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
        KnowledgeBase.objects.all().delete()
        Users.objects.all().delete()
    
    def test_update_with_permission(self):
        """测试有权限时更新成功"""
        kb = KnowledgeBase.objects.create(
            name="原始名称",
            description="原始描述",
            uploader=self.user
        )
        
        request = self.factory.put('/')
        request.user = self.user
        
        data = {'name': '更新后的名称', 'description': '更新后的描述'}
        
        serializer = KnowledgeBaseUpdateSerializer(
            kb,
            data=data,
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_kb = serializer.save()
        
        self.assertEqual(updated_kb.name, '更新后的名称')

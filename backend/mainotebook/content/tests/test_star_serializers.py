# -*- coding: utf-8 -*-

"""
收藏序列化器测试

测试收藏序列化器的数据验证、序列化功能。

验证需求：5.5, 5.9, 10.1, 10.2, 10.3, 10.10
"""

from django.test import TestCase
from rest_framework.test import APIRequestFactory
from mainotebook.system.models import Users
from mainotebook.content.models import (
    StarRecord, 
    KnowledgeBase, 
    PersonaCard
)
from mainotebook.content.serializers.star import StarRecordSerializer


class TestStarRecordSerializer(TestCase):
    """测试收藏记录序列化器"""
    
    def setUp(self):
        """测试前准备"""
        self.factory = APIRequestFactory()
        
        # 创建用户
        self.user = Users.objects.create(
            username="testuser",
            name="测试用户",
            email="test@example.com",
            avatar="avatar.jpg"
        )
        
        self.creator = Users.objects.create(
            username="creator",
            name="创建者",
            email="creator@example.com",
            avatar="creator_avatar.jpg"
        )
        
        # 创建知识库
        self.knowledge_base = KnowledgeBase.objects.create(
            name="测试知识库",
            description="知识库描述",
            uploader=self.creator,
            tags="Python,Django",
            version="1.0"
        )
        
        # 创建人设卡
        self.persona_card = PersonaCard.objects.create(
            name="测试人设卡",
            description="人设卡描述",
            uploader=self.creator,
            tags="AI,Bot",
            version="1.0"
        )
    
    def tearDown(self):
        """测试后清理"""
        StarRecord.objects.all().delete()
        KnowledgeBase.objects.all().delete()
        PersonaCard.objects.all().delete()
        Users.objects.all().delete()
    
    def test_serialize_knowledge_base_star(self):
        """测试序列化知识库收藏记录（需求 5.5, 5.9, 10.3）"""
        # 创建收藏记录
        star = StarRecord.objects.create(
            user=self.user,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge'
        )
        
        # 序列化
        serializer = StarRecordSerializer(star)
        data = serializer.data
        
        # 验证基本字段
        self.assertIn('id', data)
        self.assertEqual(data['target_id'], str(self.knowledge_base.id))
        self.assertEqual(data['target_type'], 'knowledge')
        self.assertIn('create_datetime', data)
        
        # 验证目标信息字段（需求 5.9）
        self.assertEqual(data['target_name'], "测试知识库")
        self.assertEqual(data['target_description'], "知识库描述")
        
        # 验证创建者信息（需求 5.9）
        self.assertIsNotNone(data['target_creator'])
        self.assertEqual(data['target_creator']['id'], self.creator.id)
        self.assertEqual(data['target_creator']['name'], "创建者")
        self.assertEqual(data['target_creator']['avatar'], "creator_avatar.jpg")
    
    def test_serialize_persona_card_star(self):
        """测试序列化人设卡收藏记录（需求 5.5, 5.9, 10.3）"""
        # 创建收藏记录
        star = StarRecord.objects.create(
            user=self.user,
            target_id=str(self.persona_card.id),
            target_type='persona'
        )
        
        # 序列化
        serializer = StarRecordSerializer(star)
        data = serializer.data
        
        # 验证基本字段
        self.assertEqual(data['target_id'], str(self.persona_card.id))
        self.assertEqual(data['target_type'], 'persona')
        
        # 验证目标信息字段
        self.assertEqual(data['target_name'], "测试人设卡")
        self.assertEqual(data['target_description'], "人设卡描述")
        
        # 验证创建者信息
        self.assertIsNotNone(data['target_creator'])
        self.assertEqual(data['target_creator']['id'], self.creator.id)
    
    def test_serialize_with_deleted_target(self):
        """测试序列化已删除目标的收藏记录"""
        # 创建收藏记录
        star = StarRecord.objects.create(
            user=self.user,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge'
        )
        
        # 删除知识库
        self.knowledge_base.delete()
        
        # 序列化
        serializer = StarRecordSerializer(star)
        data = serializer.data
        
        # 验证目标信息为 None
        self.assertIsNone(data['target_name'])
        self.assertIsNone(data['target_description'])
        self.assertIsNone(data['target_creator'])
    
    def test_serialize_with_nonexistent_target(self):
        """测试序列化不存在目标的收藏记录"""
        import uuid
        
        # 创建收藏记录（使用有效 UUID 但目标不存在）
        nonexistent_id = str(uuid.uuid4())
        star = StarRecord.objects.create(
            user=self.user,
            target_id=nonexistent_id,
            target_type='knowledge'
        )
        
        # 序列化
        serializer = StarRecordSerializer(star)
        data = serializer.data
        
        # 验证目标信息为 None
        self.assertIsNone(data['target_name'])
        self.assertIsNone(data['target_description'])
        self.assertIsNone(data['target_creator'])
    
    def test_read_only_fields(self):
        """测试只读字段（需求 10.1, 10.2）"""
        serializer = StarRecordSerializer()
        
        # 验证只读字段
        self.assertIn('id', serializer.Meta.read_only_fields)
        self.assertIn('create_datetime', serializer.Meta.read_only_fields)
    
    def test_response_format_consistency(self):
        """测试响应格式一致性（需求 10.10）"""
        # 创建收藏记录
        star = StarRecord.objects.create(
            user=self.user,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge'
        )
        
        # 序列化
        serializer = StarRecordSerializer(star)
        data = serializer.data
        
        # 验证所有必需字段都存在
        required_fields = [
            'id', 'target_id', 'target_type', 'target_name',
            'target_description', 'target_creator', 'create_datetime'
        ]
        
        for field in required_fields:
            self.assertIn(field, data, f"字段 {field} 应该存在于响应中")
    
    def test_multiple_stars_serialization(self):
        """测试批量序列化多个收藏记录"""
        # 创建多个收藏记录
        star1 = StarRecord.objects.create(
            user=self.user,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge'
        )
        
        star2 = StarRecord.objects.create(
            user=self.user,
            target_id=str(self.persona_card.id),
            target_type='persona'
        )
        
        # 批量序列化
        serializer = StarRecordSerializer([star1, star2], many=True)
        data = serializer.data
        
        # 验证返回两条记录
        self.assertEqual(len(data), 2)
        
        # 验证每条记录都有完整字段
        for item in data:
            self.assertIn('target_name', item)
            self.assertIn('target_creator', item)

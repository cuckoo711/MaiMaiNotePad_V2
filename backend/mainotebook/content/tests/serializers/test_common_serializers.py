# -*- coding: utf-8 -*-

"""
通用序列化器测试

测试通用序列化器基类和混入类的功能。
"""

import pytest
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory
from mainotebook.content.serializers.common import (
    UploaderInfoMixin,
    StarStatusMixin,
    UserInfoMixin,
    OwnershipValidationMixin,
    UniqueNameValidationMixin,
    AuthenticationValidationMixin,
)
from mainotebook.content.models import KnowledgeBase, StarRecord
from mainotebook.system.models import Users
from rest_framework import serializers


@pytest.mark.django_db
class TestUploaderInfoMixin:
    """测试上传者信息混入类"""
    
    def test_uploader_info_fields_exist(self, knowledge_base_factory, user_factory):
        """测试上传者信息字段存在"""
        from mainotebook.content.serializers import KnowledgeBaseSerializer
        
        user = user_factory(name="测试用户", avatar="avatar.jpg")
        kb = knowledge_base_factory(uploader=user)
        
        serializer = KnowledgeBaseSerializer(kb)
        data = serializer.data
        
        assert 'uploader_name' in data
        assert 'uploader_avatar' in data
        assert data['uploader_name'] == "测试用户"
        assert data['uploader_avatar'] == "avatar.jpg"


@pytest.mark.django_db
class TestStarStatusMixin:
    """测试收藏状态混入类"""
    
    def test_is_starred_when_user_starred(
        self, 
        knowledge_base_factory, 
        user_factory,
        star_record_factory
    ):
        """测试用户已收藏时返回 True"""
        from mainotebook.content.serializers import KnowledgeBaseSerializer
        
        user = user_factory()
        kb = knowledge_base_factory()
        star_record_factory(user=user, target_id=str(kb.id), target_type='knowledge')
        
        # 创建请求上下文
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = user
        
        serializer = KnowledgeBaseSerializer(kb, context={'request': request})
        data = serializer.data
        
        assert data['is_starred'] is True
    
    def test_is_starred_when_user_not_starred(
        self, 
        knowledge_base_factory, 
        user_factory
    ):
        """测试用户未收藏时返回 False"""
        from mainotebook.content.serializers import KnowledgeBaseSerializer
        
        user = user_factory()
        kb = knowledge_base_factory()
        
        # 创建请求上下文
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = user
        
        serializer = KnowledgeBaseSerializer(kb, context={'request': request})
        data = serializer.data
        
        assert data['is_starred'] is False
    
    def test_is_starred_when_user_not_authenticated(self, knowledge_base_factory):
        """测试用户未认证时返回 False"""
        from mainotebook.content.serializers import KnowledgeBaseSerializer
        from django.contrib.auth.models import AnonymousUser
        
        kb = knowledge_base_factory()
        
        # 创建请求上下文（匿名用户）
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = AnonymousUser()
        
        serializer = KnowledgeBaseSerializer(kb, context={'request': request})
        data = serializer.data
        
        assert data['is_starred'] is False


@pytest.mark.django_db
class TestUserInfoMixin:
    """测试用户信息混入类"""
    
    def test_user_info_fields_exist(self, comment_factory, user_factory):
        """测试用户信息字段存在"""
        from mainotebook.content.serializers import CommentSerializer
        
        user = user_factory(name="评论用户", avatar="user_avatar.jpg")
        comment = comment_factory(user=user)
        
        serializer = CommentSerializer(comment)
        data = serializer.data
        
        assert 'user_name' in data
        assert 'user_avatar' in data
        assert data['user_name'] == "评论用户"
        assert data['user_avatar'] == "user_avatar.jpg"


@pytest.mark.django_db
class TestOwnershipValidationMixin:
    """测试所有权验证混入类"""
    
    def test_validate_ownership_success(self, knowledge_base_factory, user_factory):
        """测试所有权验证成功"""
        from mainotebook.content.serializers import KnowledgeBaseUpdateSerializer
        
        user = user_factory()
        kb = knowledge_base_factory(uploader=user)
        
        serializer = KnowledgeBaseUpdateSerializer()
        # 不应该抛出异常
        serializer.validate_ownership(kb, user)
    
    def test_validate_ownership_failure(self, knowledge_base_factory, user_factory):
        """测试所有权验证失败"""
        from mainotebook.content.serializers import KnowledgeBaseUpdateSerializer
        
        owner = user_factory()
        other_user = user_factory()
        kb = knowledge_base_factory(uploader=owner)
        
        serializer = KnowledgeBaseUpdateSerializer()
        with pytest.raises(serializers.ValidationError):
            serializer.validate_ownership(kb, other_user)


@pytest.mark.django_db
class TestUniqueNameValidationMixin:
    """测试唯一名称验证混入类"""
    
    def test_validate_unique_name_success(self, knowledge_base_factory, user_factory):
        """测试名称唯一性验证成功"""
        from mainotebook.content.serializers import KnowledgeBaseCreateSerializer
        
        user = user_factory()
        knowledge_base_factory(uploader=user, name="已存在的知识库")
        
        serializer = KnowledgeBaseCreateSerializer()
        # 不应该抛出异常
        result = serializer.validate_unique_name(
            value="新知识库",
            user=user,
            model_class=KnowledgeBase
        )
        assert result == "新知识库"
    
    def test_validate_unique_name_failure(self, knowledge_base_factory, user_factory):
        """测试名称唯一性验证失败"""
        from mainotebook.content.serializers import KnowledgeBaseCreateSerializer
        
        user = user_factory()
        knowledge_base_factory(uploader=user, name="重复的知识库")
        
        serializer = KnowledgeBaseCreateSerializer()
        with pytest.raises(serializers.ValidationError):
            serializer.validate_unique_name(
                value="重复的知识库",
                user=user,
                model_class=KnowledgeBase
            )
    
    def test_validate_unique_name_with_exclude(
        self, 
        knowledge_base_factory, 
        user_factory
    ):
        """测试名称唯一性验证（排除当前实例）"""
        from mainotebook.content.serializers import KnowledgeBaseUpdateSerializer
        
        user = user_factory()
        kb = knowledge_base_factory(uploader=user, name="知识库名称")
        
        serializer = KnowledgeBaseUpdateSerializer()
        # 不应该抛出异常（排除当前实例）
        result = serializer.validate_unique_name(
            value="知识库名称",
            user=user,
            model_class=KnowledgeBase,
            exclude_instance=kb
        )
        assert result == "知识库名称"


@pytest.mark.django_db
class TestAuthenticationValidationMixin:
    """测试认证验证混入类"""
    
    def test_validate_user_authenticated_success(self, user_factory):
        """测试用户认证验证成功"""
        from mainotebook.content.serializers import KnowledgeBaseCreateSerializer
        
        user = user_factory()
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = user
        
        serializer = KnowledgeBaseCreateSerializer()
        # 不应该抛出异常
        serializer.validate_user_authenticated(request)
    
    def test_validate_user_authenticated_failure(self):
        """测试用户认证验证失败"""
        from mainotebook.content.serializers import KnowledgeBaseCreateSerializer
        from django.contrib.auth.models import AnonymousUser
        
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = AnonymousUser()
        
        serializer = KnowledgeBaseCreateSerializer()
        with pytest.raises(serializers.ValidationError):
            serializer.validate_user_authenticated(request)


@pytest.mark.django_db
class TestContentCreateSerializer:
    """测试内容创建序列化器基类"""
    
    def test_create_with_uploader(self, user_factory):
        """测试创建时自动设置上传者"""
        from mainotebook.content.serializers import KnowledgeBaseCreateSerializer
        
        user = user_factory()
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = user
        
        data = {
            'name': '测试知识库',
            'description': '测试描述',
            'copyright_owner': '版权所有者',
            'content': '内容',
            'tags': '标签1,标签2',
            'version': '1.0'
        }
        
        serializer = KnowledgeBaseCreateSerializer(
            data=data,
            context={'request': request}
        )
        assert serializer.is_valid(), serializer.errors
        kb = serializer.save()
        
        assert kb.uploader == user
        assert kb.name == '测试知识库'


@pytest.mark.django_db
class TestContentUpdateSerializer:
    """测试内容更新序列化器基类"""
    
    def test_update_with_permission(self, knowledge_base_factory, user_factory):
        """测试有权限时更新成功"""
        from mainotebook.content.serializers import KnowledgeBaseUpdateSerializer
        
        user = user_factory()
        kb = knowledge_base_factory(uploader=user, name="原始名称")
        
        factory = APIRequestFactory()
        request = factory.put('/')
        request.user = user
        
        data = {
            'name': '更新后的名称',
            'description': '更新后的描述',
            'copyright_owner': '版权所有者',
            'content': '更新后的内容',
            'tags': '新标签',
            'version': '2.0'
        }
        
        serializer = KnowledgeBaseUpdateSerializer(
            kb,
            data=data,
            context={'request': request}
        )
        assert serializer.is_valid(), serializer.errors
        updated_kb = serializer.save()
        
        assert updated_kb.name == '更新后的名称'
        assert updated_kb.description == '更新后的描述'
    
    def test_update_without_permission(self, knowledge_base_factory, user_factory):
        """测试无权限时更新失败"""
        from mainotebook.content.serializers import KnowledgeBaseUpdateSerializer
        
        owner = user_factory()
        other_user = user_factory()
        kb = knowledge_base_factory(uploader=owner, name="原始名称")
        
        factory = APIRequestFactory()
        request = factory.put('/')
        request.user = other_user
        
        data = {
            'name': '尝试更新的名称',
            'description': '尝试更新的描述',
            'copyright_owner': '版权所有者',
            'content': '尝试更新的内容',
            'tags': '新标签',
            'version': '2.0'
        }
        
        serializer = KnowledgeBaseUpdateSerializer(
            kb,
            data=data,
            context={'request': request}
        )
        assert not serializer.is_valid()
        assert '只有创建者可以修改知识库' in str(serializer.errors)

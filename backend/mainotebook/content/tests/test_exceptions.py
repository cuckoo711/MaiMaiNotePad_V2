"""
自定义异常类测试

测试内容管理模块的自定义异常类和异常处理器。
"""

import pytest
from django.test import TestCase, RequestFactory
from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import ValidationError as DRFValidationError

from mainotebook.content.exceptions import (
    ContentException,
    PermissionDeniedException,
    ResourceNotFoundException,
    ValidationException,
    ConflictException,
    custom_exception_handler,
)


class TestContentException(TestCase):
    """测试 ContentException 基类"""
    
    def test_content_exception_default_code(self):
        """测试默认状态码为 400"""
        exc = ContentException("测试错误")
        assert exc.message == "测试错误"
        assert exc.code == 400
    
    def test_content_exception_custom_code(self):
        """测试自定义状态码"""
        exc = ContentException("测试错误", code=500)
        assert exc.message == "测试错误"
        assert exc.code == 500
    
    def test_content_exception_str(self):
        """测试异常字符串表示"""
        exc = ContentException("测试错误")
        assert str(exc) == "测试错误"


class TestPermissionDeniedException(TestCase):
    """测试 PermissionDeniedException"""
    
    def test_default_message(self):
        """测试默认错误消息"""
        exc = PermissionDeniedException()
        assert exc.message == "您没有权限执行此操作"
        assert exc.code == 403
    
    def test_custom_message(self):
        """测试自定义错误消息"""
        exc = PermissionDeniedException("无法访问此资源")
        assert exc.message == "无法访问此资源"
        assert exc.code == 403


class TestResourceNotFoundException(TestCase):
    """测试 ResourceNotFoundException"""
    
    def test_default_message(self):
        """测试默认错误消息"""
        exc = ResourceNotFoundException()
        assert exc.message == "请求的资源不存在"
        assert exc.code == 404
    
    def test_custom_message(self):
        """测试自定义错误消息"""
        exc = ResourceNotFoundException("知识库不存在")
        assert exc.message == "知识库不存在"
        assert exc.code == 404


class TestValidationException(TestCase):
    """测试 ValidationException"""
    
    def test_validation_exception(self):
        """测试验证异常"""
        exc = ValidationException("数据格式不正确")
        assert exc.message == "数据格式不正确"
        assert exc.code == 400


class TestConflictException(TestCase):
    """测试 ConflictException"""
    
    def test_conflict_exception(self):
        """测试冲突异常"""
        exc = ConflictException("资源已存在")
        assert exc.message == "资源已存在"
        assert exc.code == 409


class TestCustomExceptionHandler(TestCase):
    """测试自定义异常处理器"""
    
    def setUp(self):
        """设置测试环境"""
        self.factory = APIRequestFactory()
    
    def test_handle_content_exception(self):
        """测试处理 ContentException"""
        request = self.factory.get('/test/')
        context = {'request': request}
        
        exc = ValidationException("测试验证错误")
        response = custom_exception_handler(exc, context)
        
        assert response is not None
        assert response.status_code == 400
    
    def test_handle_permission_denied_exception(self):
        """测试处理 PermissionDeniedException"""
        request = self.factory.get('/test/')
        context = {'request': request}
        
        exc = PermissionDeniedException()
        response = custom_exception_handler(exc, context)
        
        assert response is not None
        assert response.status_code == 403
    
    def test_handle_resource_not_found_exception(self):
        """测试处理 ResourceNotFoundException"""
        request = self.factory.get('/test/')
        context = {'request': request}
        
        exc = ResourceNotFoundException()
        response = custom_exception_handler(exc, context)
        
        assert response is not None
        assert response.status_code == 404
    
    def test_handle_conflict_exception(self):
        """测试处理 ConflictException"""
        request = self.factory.get('/test/')
        context = {'request': request}
        
        exc = ConflictException("重复操作")
        response = custom_exception_handler(exc, context)
        
        assert response is not None
        assert response.status_code == 409
    
    def test_handle_drf_exception(self):
        """测试处理 DRF 异常"""
        request = self.factory.get('/test/')
        context = {'request': request}
        
        exc = DRFValidationError("DRF 验证错误")
        response = custom_exception_handler(exc, context)
        
        assert response is not None
        assert response.status_code == 400
    
    def test_handle_generic_exception(self):
        """测试处理通用异常"""
        request = self.factory.get('/test/')
        context = {'request': request}
        
        exc = Exception("未知错误")
        response = custom_exception_handler(exc, context)
        
        assert response is not None
        assert response.status_code == 500


class TestExceptionInheritance(TestCase):
    """测试异常继承关系"""
    
    def test_all_exceptions_inherit_from_content_exception(self):
        """测试所有自定义异常都继承自 ContentException"""
        assert issubclass(PermissionDeniedException, ContentException)
        assert issubclass(ResourceNotFoundException, ContentException)
        assert issubclass(ValidationException, ContentException)
        assert issubclass(ConflictException, ContentException)
    
    def test_all_exceptions_inherit_from_exception(self):
        """测试所有自定义异常都继承自 Exception"""
        assert issubclass(ContentException, Exception)
        assert issubclass(PermissionDeniedException, Exception)
        assert issubclass(ResourceNotFoundException, Exception)
        assert issubclass(ValidationException, Exception)
        assert issubclass(ConflictException, Exception)

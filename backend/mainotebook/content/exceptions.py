"""
内容管理自定义异常类

本模块定义了内容管理相关的自定义异常类和异常处理器。
所有自定义异常都继承自 ContentException 基类。
"""

import logging
from typing import Any, Dict, Optional
from rest_framework.views import exception_handler, set_rollback
from rest_framework.response import Response
from mainotebook.utils.json_response import ErrorResponse

logger = logging.getLogger(__name__)


class ContentException(Exception):
    """内容相关异常基类
    
    所有内容管理相关的自定义异常都应该继承此类。
    
    Attributes:
        message: 错误消息
        code: HTTP 状态码
    """
    
    def __init__(self, message: str, code: int = 400):
        """初始化异常
        
        Args:
            message: 错误消息
            code: HTTP 状态码，默认为 400
        """
        self.message = message
        self.code = code
        super().__init__(self.message)


class PermissionDeniedException(ContentException):
    """权限拒绝异常
    
    当用户尝试执行没有权限的操作时抛出此异常。
    HTTP 状态码为 403 Forbidden。
    """
    
    def __init__(self, message: str = "您没有权限执行此操作"):
        """初始化权限拒绝异常
        
        Args:
            message: 错误消息，默认为"您没有权限执行此操作"
        """
        super().__init__(message, code=403)


class ResourceNotFoundException(ContentException):
    """资源不存在异常
    
    当请求的资源不存在时抛出此异常。
    HTTP 状态码为 404 Not Found。
    """
    
    def __init__(self, message: str = "请求的资源不存在"):
        """初始化资源不存在异常
        
        Args:
            message: 错误消息，默认为"请求的资源不存在"
        """
        super().__init__(message, code=404)


class ValidationException(ContentException):
    """验证异常
    
    当数据验证失败时抛出此异常。
    HTTP 状态码为 400 Bad Request。
    """
    
    def __init__(self, message: str):
        """初始化验证异常
        
        Args:
            message: 错误消息
        """
        super().__init__(message, code=400)


class ConflictException(ContentException):
    """冲突异常
    
    当操作与当前状态冲突时抛出此异常。
    例如：重复收藏、重复提交审核等。
    HTTP 状态码为 409 Conflict。
    """
    
    def __init__(self, message: str):
        """初始化冲突异常
        
        Args:
            message: 错误消息
        """
        super().__init__(message, code=409)


def custom_exception_handler(exc, context):
    """自定义异常处理器
    
    处理自定义异常并返回统一格式的错误响应。
    此处理器会：
    1. 首先调用 DRF 默认的异常处理器
    2. 处理自定义的 ContentException 及其子类
    3. 处理其他 DRF 异常
    4. 处理未捕获的异常
    
    Args:
        exc: 异常对象
        context: 异常上下文，包含 view 和 request 等信息
        
    Returns:
        ErrorResponse: 统一格式的错误响应
    """
    # 调用 DRF 默认的异常处理器
    response = exception_handler(exc, context)
    
    # 获取请求信息用于日志记录
    request = context.get('request')
    view = context.get('view')
    
    # 处理自定义异常
    if isinstance(exc, ContentException):
        # 设置数据库回滚
        set_rollback()
        
        # 记录警告日志
        logger.warning(
            f"自定义异常: {exc.__class__.__name__} - {exc.message}",
            extra={
                'user_id': getattr(request.user, 'id', None) if request and hasattr(request, 'user') else None,
                'path': request.path if request else None,
                'method': request.method if request else None,
                'view': view.__class__.__name__ if view else None,
            }
        )
        
        # 返回统一格式的错误响应
        return ErrorResponse(msg=exc.message, code=exc.code, status=exc.code)
    
    # 处理其他 DRF 异常
    if response is not None:
        # 记录警告日志
        logger.warning(
            f"DRF 异常: {exc.__class__.__name__} - {str(exc)}",
            extra={
                'user_id': getattr(request.user, 'id', None) if request and hasattr(request, 'user') else None,
                'path': request.path if request else None,
                'method': request.method if request else None,
                'view': view.__class__.__name__ if view else None,
            }
        )
        
        # 提取错误消息
        msg = str(exc)
        if hasattr(response, 'data') and isinstance(response.data, dict):
            # 如果响应数据是字典，尝试提取详细信息
            if 'detail' in response.data:
                msg = response.data['detail']
            elif 'message' in response.data:
                msg = response.data['message']
        
        return ErrorResponse(msg=msg, code=response.status_code, status=response.status_code)
    
    # 处理未捕获的异常
    logger.error(
        f"未处理的异常: {exc.__class__.__name__} - {str(exc)}",
        exc_info=True,
        extra={
            'user_id': getattr(request.user, 'id', None) if request and hasattr(request, 'user') else None,
            'path': request.path if request else None,
            'method': request.method if request else None,
            'view': view.__class__.__name__ if view else None,
        }
    )
    
    return ErrorResponse(msg='服务器内部错误', code=500, status=500)

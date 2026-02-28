"""
内容管理应用的自定义权限类

本模块定义了内容管理相关的权限验证类，用于控制用户对资源的访问权限。
"""

from rest_framework import permissions
from django.utils import timezone


class IsOwnerOrReadOnly(permissions.BasePermission):
    """仅创建者可以修改和删除
    
    该权限类允许所有用户读取资源，但只有资源的创建者可以修改或删除资源。
    适用于知识库、人设卡等用户创建的内容。
    """
    
    def has_object_permission(self, request, view, obj):
        """检查对象级权限
        
        Args:
            request: HTTP 请求对象
            view: 视图对象
            obj: 要访问的对象
            
        Returns:
            bool: 是否有权限访问
        """
        # 读取权限允许所有请求（GET, HEAD, OPTIONS）
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 写入权限仅允许创建者
        # 检查对象是否有 uploader 属性
        if hasattr(obj, 'uploader'):
            return obj.uploader == request.user
        
        # 如果对象没有 uploader 属性，拒绝访问
        return False


class IsModeratorOrAdmin(permissions.BasePermission):
    """仅审核员或管理员可以访问
    
    该权限类用于审核相关的功能，只有审核员、管理员或超级管理员可以访问。
    """
    
    def has_permission(self, request, view):
        """检查用户级权限
        
        Args:
            request: HTTP 请求对象
            view: 视图对象
            
        Returns:
            bool: 是否有权限访问
        """
        # 检查用户是否已认证
        if not request.user or not request.user.is_authenticated:
            return False
        
        # 检查用户是否为审核员、管理员或超级管理员
        return (
            getattr(request.user, 'is_moderator', False) or
            getattr(request.user, 'is_staff', False) or
            getattr(request.user, 'is_superuser', False)
        )


class IsAdminUser(permissions.BasePermission):
    """仅管理员可以访问
    
    该权限类用于管理员专属功能，只有管理员或超级管理员可以访问。
    适用于用户管理、禁言、封禁等敏感操作。
    """
    
    def has_permission(self, request, view):
        """检查用户级权限
        
        Args:
            request: HTTP 请求对象
            view: 视图对象
            
        Returns:
            bool: 是否有权限访问
        """
        # 检查用户是否已认证
        if not request.user or not request.user.is_authenticated:
            return False
        
        # 检查用户是否为管理员或超级管理员
        return (
            getattr(request.user, 'is_staff', False) or
            getattr(request.user, 'is_superuser', False)
        )


class CanComment(permissions.BasePermission):
    """可以发表评论（未被禁言）
    
    该权限类用于评论功能，检查用户是否被禁言。
    被禁言的用户无法发表评论或回复。
    """
    
    def has_permission(self, request, view):
        """检查用户级权限
        
        Args:
            request: HTTP 请求对象
            view: 视图对象
            
        Returns:
            bool: 是否有权限发表评论
        """
        # 检查用户是否已认证
        if not request.user or not request.user.is_authenticated:
            return False
        
        # 检查用户是否被禁言
        if getattr(request.user, 'is_muted', False):
            # 如果设置了禁言截止时间，检查是否已过期
            muted_until = getattr(request.user, 'muted_until', None)
            if muted_until:
                # 如果禁言时间未过期，拒绝访问
                if muted_until > timezone.now():
                    return False
            else:
                # 如果没有设置截止时间，表示永久禁言
                return False
        
        return True

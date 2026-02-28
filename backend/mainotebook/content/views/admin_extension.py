# -*- coding: utf-8 -*-

"""
管理员扩展视图集

提供用户管理功能，包括禁言、封禁、解封和角色管理。
仅管理员可访问。
"""

from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from mainotebook.utils.json_response import DetailResponse, ErrorResponse
from mainotebook.system.models import Users
from mainotebook.content.permissions import IsAdminUser


class AdminExtensionViewSet(viewsets.ViewSet):
    """管理员扩展视图集
    
    提供用户管理功能（禁言、封禁、角色管理）。
    
    操作：
    - mute: 禁言用户
    - ban: 封禁用户
    - unban: 解封用户
    - update_role: 更新用户角色
    - get_status: 获取用户状态
    """
    
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    @swagger_auto_schema(
        operation_summary='禁言用户',
        operation_description='设置用户禁言状态和禁言时长，禁言期间用户无法发表评论',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['duration'],
            properties={
                'duration': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='禁言时长，格式：数字+单位（h=小时，d=天，w=周，m=月），例如：1h、7d、1w、1m。使用 "permanent" 表示永久禁言'
                ),
                'reason': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='禁言原因'
                ),
            }
        ),
        responses={
            200: openapi.Response(
                description='禁言成功',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='用户ID'),
                        'is_muted': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='是否被禁言'),
                        'muted_until': openapi.Schema(type=openapi.TYPE_STRING, description='禁言截止时间'),
                        'mute_reason': openapi.Schema(type=openapi.TYPE_STRING, description='禁言原因'),
                    }
                )
            ),
            400: '参数错误',
            403: '权限不足',
            404: '用户不存在'
        }
    )
    @action(methods=['POST'], detail=True)
    def mute(self, request, pk=None):
        """禁言用户
        
        Args:
            request: HTTP 请求对象
            pk: 用户ID
            
        Request Body:
            duration (str): 禁言时长，格式：数字+单位（h/d/w/m）或 "permanent"
            reason (str, optional): 禁言原因
            
        Returns:
            Response: 包含禁言结果的响应
        """
        # 获取请求数据
        duration = request.data.get('duration')
        reason = request.data.get('reason', '')
        
        # 验证参数
        if not duration:
            return ErrorResponse(
                msg="禁言时长不能为空",
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 获取目标用户
            user = Users.objects.filter(id=pk).first()
            if not user:
                return ErrorResponse(
                    msg="用户不存在",
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 验证权限：不能禁言管理员或超级管理员
            if user.is_staff or user.is_superuser:
                return ErrorResponse(
                    msg="不能禁言管理员或超级管理员",
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # 解析禁言时长
            muted_until = self._parse_duration(duration)
            
            # 设置禁言状态
            user.is_muted = True
            user.muted_until = muted_until
            user.mute_reason = reason or "违反社区行为规范"
            user.save()
            
            # 返回结果
            result = {
                'user_id': user.id,
                'is_muted': True,
                'muted_until': muted_until.isoformat() if muted_until else None,
                'mute_reason': user.mute_reason
            }
            
            return DetailResponse(data=result, msg="禁言成功")
            
        except ValueError as e:
            return ErrorResponse(
                msg=str(e),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return ErrorResponse(
                msg=f"禁言失败: {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_summary='封禁用户',
        operation_description='封禁用户账号，封禁期间用户无法登录',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['duration'],
            properties={
                'duration': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='封禁时长，格式：数字+单位（h=小时，d=天，w=周，m=月），例如：1h、7d、1w、1m。使用 "permanent" 表示永久封禁'
                ),
                'reason': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='封禁原因'
                ),
            }
        ),
        responses={
            200: openapi.Response(
                description='封禁成功',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='用户ID'),
                        'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='账号是否激活'),
                        'locked_until': openapi.Schema(type=openapi.TYPE_STRING, description='封禁截止时间'),
                        'ban_reason': openapi.Schema(type=openapi.TYPE_STRING, description='封禁原因'),
                    }
                )
            ),
            400: '参数错误',
            403: '权限不足',
            404: '用户不存在'
        }
    )
    @action(methods=['POST'], detail=True)
    def ban(self, request, pk=None):
        """封禁用户
        
        Args:
            request: HTTP 请求对象
            pk: 用户ID
            
        Request Body:
            duration (str): 封禁时长，格式：数字+单位（h/d/w/m）或 "permanent"
            reason (str, optional): 封禁原因
            
        Returns:
            Response: 包含封禁结果的响应
        """
        # 获取请求数据
        duration = request.data.get('duration')
        reason = request.data.get('reason', '')
        
        # 验证参数
        if not duration:
            return ErrorResponse(
                msg="封禁时长不能为空",
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 获取目标用户
            user = Users.objects.filter(id=pk).first()
            if not user:
                return ErrorResponse(
                    msg="用户不存在",
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 验证权限：不能封禁管理员或超级管理员
            if user.is_staff or user.is_superuser:
                return ErrorResponse(
                    msg="不能封禁管理员或超级管理员",
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # 解析封禁时长
            locked_until = self._parse_duration(duration)
            
            # 设置封禁状态
            user.is_active = False
            user.locked_until = locked_until
            user.ban_reason = reason or "违反社区行为规范"
            user.save()
            
            # 返回结果
            result = {
                'user_id': user.id,
                'is_active': False,
                'locked_until': locked_until.isoformat() if locked_until else None,
                'ban_reason': user.ban_reason
            }
            
            return DetailResponse(data=result, msg="封禁成功")
            
        except ValueError as e:
            return ErrorResponse(
                msg=str(e),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return ErrorResponse(
                msg=f"封禁失败: {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_summary='解封用户',
        operation_description='解除用户的封禁和禁言状态，恢复用户访问权限',
        responses={
            200: openapi.Response(
                description='解封成功',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='用户ID'),
                        'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='账号是否激活'),
                        'is_muted': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='是否被禁言'),
                    }
                )
            ),
            403: '权限不足',
            404: '用户不存在'
        }
    )
    @action(methods=['POST'], detail=True)
    def unban(self, request, pk=None):
        """解封用户
        
        Args:
            request: HTTP 请求对象
            pk: 用户ID
            
        Returns:
            Response: 包含解封结果的响应
        """
        try:
            # 获取目标用户
            user = Users.objects.filter(id=pk).first()
            if not user:
                return ErrorResponse(
                    msg="用户不存在",
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 验证权限：不能解封管理员或超级管理员（虽然他们不应该被封禁）
            if user.is_staff or user.is_superuser:
                return ErrorResponse(
                    msg="不能对管理员或超级管理员执行此操作",
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # 清除封禁和禁言状态
            user.is_active = True
            user.locked_until = None
            user.ban_reason = None
            user.is_muted = False
            user.muted_until = None
            user.mute_reason = None
            user.save()
            
            # 返回结果
            result = {
                'user_id': user.id,
                'is_active': True,
                'is_muted': False
            }
            
            return DetailResponse(data=result, msg="解封成功")
            
        except Exception as e:
            return ErrorResponse(
                msg=f"解封失败: {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_summary='更新用户角色',
        operation_description='修改用户的角色（普通用户、审核员、管理员）',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['role'],
            properties={
                'role': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='用户角色：user（普通用户）、moderator（审核员）、admin（管理员）',
                    enum=['user', 'moderator', 'admin']
                ),
            }
        ),
        responses={
            200: openapi.Response(
                description='角色更新成功',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='用户ID'),
                        'role': openapi.Schema(type=openapi.TYPE_STRING, description='用户角色'),
                        'is_moderator': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='是否为审核员'),
                        'is_staff': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='是否为管理员'),
                    }
                )
            ),
            400: '参数错误',
            403: '权限不足',
            404: '用户不存在'
        }
    )
    @action(methods=['PUT'], detail=True, url_path='role')
    def update_role(self, request, pk=None):
        """更新用户角色
        
        Args:
            request: HTTP 请求对象
            pk: 用户ID
            
        Request Body:
            role (str): 用户角色，可选值：'user'、'moderator'、'admin'
            
        Returns:
            Response: 包含角色更新结果的响应
        """
        # 获取请求数据
        role = request.data.get('role')
        
        # 验证参数
        if not role:
            return ErrorResponse(
                msg="角色不能为空",
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if role not in ['user', 'moderator', 'admin']:
            return ErrorResponse(
                msg="无效的角色，可选值：user、moderator、admin",
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 获取目标用户
            user = Users.objects.filter(id=pk).first()
            if not user:
                return ErrorResponse(
                    msg="用户不存在",
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 验证权限：不能修改超级管理员的角色
            if user.is_superuser:
                return ErrorResponse(
                    msg="不能修改超级管理员的角色",
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # 验证权限：普通管理员不能将用户提升为管理员
            if role == 'admin' and not request.user.is_superuser:
                return ErrorResponse(
                    msg="只有超级管理员可以设置管理员角色",
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # 更新角色
            if role == 'user':
                user.is_moderator = False
                user.is_staff = False
            elif role == 'moderator':
                user.is_moderator = True
                user.is_staff = False
            elif role == 'admin':
                user.is_moderator = False
                user.is_staff = True
            
            user.save()
            
            # 返回结果
            result = {
                'user_id': user.id,
                'role': role,
                'is_moderator': user.is_moderator,
                'is_staff': user.is_staff
            }
            
            return DetailResponse(data=result, msg="角色更新成功")
            
        except Exception as e:
            return ErrorResponse(
                msg=f"角色更新失败: {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_summary='获取用户状态',
        operation_description='获取用户的禁言、封禁和角色信息',
        responses={
            200: openapi.Response(
                description='用户状态信息',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='用户ID'),
                        'username': openapi.Schema(type=openapi.TYPE_STRING, description='用户名'),
                        'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='账号是否激活'),
                        'is_muted': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='是否被禁言'),
                        'muted_until': openapi.Schema(type=openapi.TYPE_STRING, description='禁言截止时间'),
                        'mute_reason': openapi.Schema(type=openapi.TYPE_STRING, description='禁言原因'),
                        'locked_until': openapi.Schema(type=openapi.TYPE_STRING, description='封禁截止时间'),
                        'ban_reason': openapi.Schema(type=openapi.TYPE_STRING, description='封禁原因'),
                        'role': openapi.Schema(type=openapi.TYPE_STRING, description='用户角色'),
                        'is_moderator': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='是否为审核员'),
                        'is_staff': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='是否为管理员'),
                        'is_superuser': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='是否为超级管理员'),
                    }
                )
            ),
            404: '用户不存在'
        }
    )
    @action(methods=['GET'], detail=True, url_path='status')
    def get_status(self, request, pk=None):
        """获取用户状态
        
        Args:
            request: HTTP 请求对象
            pk: 用户ID
            
        Returns:
            Response: 包含用户状态信息的响应
        """
        try:
            # 获取目标用户
            user = Users.objects.filter(id=pk).first()
            if not user:
                return ErrorResponse(
                    msg="用户不存在",
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 确定用户角色
            if user.is_superuser:
                role = 'superadmin'
            elif user.is_staff:
                role = 'admin'
            elif user.is_moderator:
                role = 'moderator'
            else:
                role = 'user'
            
            # 构建状态信息
            status_data = {
                'user_id': user.id,
                'username': user.username,
                'is_active': user.is_active,
                'is_muted': user.is_muted,
                'muted_until': user.muted_until.isoformat() if user.muted_until else None,
                'mute_reason': user.mute_reason,
                'locked_until': user.locked_until.isoformat() if user.locked_until else None,
                'ban_reason': user.ban_reason,
                'role': role,
                'is_moderator': user.is_moderator,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser
            }
            
            return DetailResponse(data=status_data, msg="获取成功")
            
        except Exception as e:
            return ErrorResponse(
                msg=f"获取用户状态失败: {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _parse_duration(self, duration: str) -> datetime | None:
        """解析时长字符串
        
        Args:
            duration: 时长字符串，格式：数字+单位（h/d/w/m）或 "permanent"
            
        Returns:
            datetime | None: 截止时间，None 表示永久
            
        Raises:
            ValueError: 当时长格式无效时
        """
        if duration.lower() == 'permanent':
            return None
        
        # 解析时长
        try:
            # 提取数字和单位
            if duration[-1] not in ['h', 'd', 'w', 'm']:
                raise ValueError("无效的时长单位，可选值：h（小时）、d（天）、w（周）、m（月）")
            
            value = int(duration[:-1])
            unit = duration[-1]
            
            if value <= 0:
                raise ValueError("时长必须大于 0")
            
            # 计算截止时间
            now = timezone.now()
            if unit == 'h':
                return now + timedelta(hours=value)
            elif unit == 'd':
                return now + timedelta(days=value)
            elif unit == 'w':
                return now + timedelta(weeks=value)
            elif unit == 'm':
                return now + timedelta(days=value * 30)  # 简化处理，1个月 = 30天
            
        except (ValueError, IndexError) as e:
            raise ValueError(f"无效的时长格式: {duration}。正确格式：数字+单位（h/d/w/m），例如：1h、7d、1w、1m")

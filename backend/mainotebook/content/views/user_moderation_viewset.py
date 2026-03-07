"""用户禁言封禁管理ViewSet

本模块提供用户禁言和封禁管理的API端点，包括：
- 禁言/解除禁言操作
- 封禁/解除封禁操作
- 修改时长操作
- 批量操作
- 列表查询
- 操作日志查询
- 数据导出

所有端点都需要IsModerationAdmin权限。
"""

import logging
import csv
from io import StringIO, BytesIO
from datetime import datetime
from typing import Optional

from django.http import HttpResponse
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request

from mainotebook.system.models import Users
from mainotebook.content.models import UserMuteRecord, UserModerationLog
from mainotebook.content.permissions import IsModerationAdmin
from mainotebook.content.services.user_moderation_service import UserModerationService
from mainotebook.content.utils.duration_formatter import DurationFormatter

logger = logging.getLogger(__name__)


class UserModerationViewSet(viewsets.ViewSet):
    """用户禁言封禁管理ViewSet
    
    提供14个API端点用于管理用户禁言和封禁：
    - mute: 禁言用户
    - unmute: 解除禁言
    - ban: 封禁用户
    - unban: 解除封禁
    - modify_duration: 修改时长
    - batch_mute: 批量禁言
    - batch_ban: 批量封禁
    - batch_unmute: 批量解除禁言
    - batch_unban: 批量解除封禁
    - mute_list: 禁言列表
    - ban_list: 封禁列表
    - auto_mute_list: AI自动禁言列表
    - logs: 操作日志
    - export: 导出数据
    """
    
    permission_classes = [IsModerationAdmin]
    
    def _get_client_info(self, request: Request) -> tuple:
        """获取客户端信息（IP地址和User-Agent）
        
        Args:
            request: HTTP请求对象
            
        Returns:
            tuple: (ip_address, user_agent)
        """
        ip_address = request.META.get('REMOTE_ADDR', '')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        return ip_address, user_agent
    
    @action(methods=['POST'], detail=False)
    def mute(self, request: Request) -> Response:
        """禁言用户
        
        POST /api/content/moderation/mute/
        
        请求参数：
            user_id (int): 被禁言用户ID
            duration (str): 时长（如"3d"、"permanent"）
            reason (str): 禁言原因
            
        Returns:
            Response: 禁言结果
        """
        try:
            # 获取请求参数
            user_id = request.data.get('user_id')
            duration = request.data.get('duration')
            reason = request.data.get('reason')
            
            # 参数验证
            if not user_id:
                return Response({
                    'code': 4000,
                    'msg': '用户ID不能为空',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not duration:
                return Response({
                    'code': 4000,
                    'msg': '时长不能为空',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not reason:
                return Response({
                    'code': 4000,
                    'msg': '禁言原因不能为空',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取客户端信息
            ip_address, user_agent = self._get_client_info(request)
            
            # 调用服务层执行禁言
            result = UserModerationService.mute_user(
                user_id=user_id,
                duration=duration,
                reason=reason,
                operator_id=request.user.id,
                mute_type='manual',
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(
                "禁言成功: operator=%s, user_id=%s, duration=%s",
                request.user.username, user_id, duration
            )
            
            return Response({
                'code': 2000,
                'msg': '禁言成功',
                'data': result
            }, status=status.HTTP_200_OK)
            
        except Users.DoesNotExist:
            return Response({
                'code': 4004,
                'msg': '用户不存在',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)
        except PermissionError as e:
            return Response({
                'code': 4003,
                'msg': str(e),
                'data': None
            }, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            return Response({
                'code': 4000,
                'msg': str(e),
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("禁言操作失败: %s", str(e))
            return Response({
                'code': 5000,
                'msg': f'操作失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(methods=['POST'], detail=False)
    def unmute(self, request: Request) -> Response:
        """解除禁言
        
        POST /api/content/moderation/unmute/
        
        请求参数：
            user_id (int): 被解除禁言用户ID
            reason (str, 可选): 解除原因
            
        Returns:
            Response: 解除结果
        """
        try:
            # 获取请求参数
            user_id = request.data.get('user_id')
            reason = request.data.get('reason')
            
            # 参数验证
            if not user_id:
                return Response({
                    'code': 4000,
                    'msg': '用户ID不能为空',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取客户端信息
            ip_address, user_agent = self._get_client_info(request)
            
            # 调用服务层执行解除禁言
            result = UserModerationService.unmute_user(
                user_id=user_id,
                operator_id=request.user.id,
                reason=reason,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(
                "解除禁言成功: operator=%s, user_id=%s",
                request.user.username, user_id
            )
            
            return Response({
                'code': 2000,
                'msg': '解除禁言成功',
                'data': result
            }, status=status.HTTP_200_OK)
            
        except Users.DoesNotExist:
            return Response({
                'code': 4004,
                'msg': '用户不存在',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)
        except PermissionError as e:
            return Response({
                'code': 4003,
                'msg': str(e),
                'data': None
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.exception("解除禁言操作失败: %s", str(e))
            return Response({
                'code': 5000,
                'msg': f'操作失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(methods=['POST'], detail=False)
    def ban(self, request: Request) -> Response:
        """封禁用户
        
        POST /api/content/moderation/ban/
        
        请求参数：
            user_id (int): 被封禁用户ID
            duration (str): 时长（如"7d"、"permanent"）
            reason (str): 封禁原因
            
        Returns:
            Response: 封禁结果
        """
        try:
            # 获取请求参数
            user_id = request.data.get('user_id')
            duration = request.data.get('duration')
            reason = request.data.get('reason')
            
            # 参数验证
            if not user_id:
                return Response({
                    'code': 4000,
                    'msg': '用户ID不能为空',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not duration:
                return Response({
                    'code': 4000,
                    'msg': '时长不能为空',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not reason:
                return Response({
                    'code': 4000,
                    'msg': '封禁原因不能为空',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取客户端信息
            ip_address, user_agent = self._get_client_info(request)
            
            # 调用服务层执行封禁
            result = UserModerationService.ban_user(
                user_id=user_id,
                duration=duration,
                reason=reason,
                operator_id=request.user.id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(
                "封禁成功: operator=%s, user_id=%s, duration=%s",
                request.user.username, user_id, duration
            )
            
            return Response({
                'code': 2000,
                'msg': '封禁成功',
                'data': result
            }, status=status.HTTP_200_OK)
            
        except Users.DoesNotExist:
            return Response({
                'code': 4004,
                'msg': '用户不存在',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)
        except PermissionError as e:
            return Response({
                'code': 4003,
                'msg': str(e),
                'data': None
            }, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            return Response({
                'code': 4000,
                'msg': str(e),
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("封禁操作失败: %s", str(e))
            return Response({
                'code': 5000,
                'msg': f'操作失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(methods=['POST'], detail=False)
    def unban(self, request: Request) -> Response:
        """解除封禁
        
        POST /api/content/moderation/unban/
        
        请求参数：
            user_id (int): 被解除封禁用户ID
            reason (str, 可选): 解除原因
            
        Returns:
            Response: 解除结果
        """
        try:
            # 获取请求参数
            user_id = request.data.get('user_id')
            reason = request.data.get('reason')
            
            # 参数验证
            if not user_id:
                return Response({
                    'code': 4000,
                    'msg': '用户ID不能为空',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取客户端信息
            ip_address, user_agent = self._get_client_info(request)
            
            # 调用服务层执行解除封禁
            result = UserModerationService.unban_user(
                user_id=user_id,
                operator_id=request.user.id,
                reason=reason,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(
                "解除封禁成功: operator=%s, user_id=%s",
                request.user.username, user_id
            )
            
            return Response({
                'code': 2000,
                'msg': '解除封禁成功',
                'data': result
            }, status=status.HTTP_200_OK)
            
        except Users.DoesNotExist:
            return Response({
                'code': 4004,
                'msg': '用户不存在',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)
        except PermissionError as e:
            return Response({
                'code': 4003,
                'msg': str(e),
                'data': None
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.exception("解除封禁操作失败: %s", str(e))
            return Response({
                'code': 5000,
                'msg': f'操作失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(methods=['PUT'], detail=False, url_path='modify-duration')
    def modify_duration(self, request: Request) -> Response:
        """修改时长
        
        PUT /api/content/moderation/modify-duration/
        
        请求参数：
            user_id (int): 用户ID
            operation_type (str): 操作类型（"mute"或"ban"）
            new_duration (str): 新时长
            reason (str): 修改原因
            
        Returns:
            Response: 修改结果
        """
        try:
            # 获取请求参数
            user_id = request.data.get('user_id')
            operation_type = request.data.get('operation_type')
            new_duration = request.data.get('new_duration')
            reason = request.data.get('reason')
            
            # 参数验证
            if not user_id:
                return Response({
                    'code': 4000,
                    'msg': '用户ID不能为空',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not operation_type or operation_type not in ['mute', 'ban']:
                return Response({
                    'code': 4000,
                    'msg': '操作类型必须是"mute"或"ban"',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not new_duration:
                return Response({
                    'code': 4000,
                    'msg': '新时长不能为空',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not reason:
                return Response({
                    'code': 4000,
                    'msg': '修改原因不能为空',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取客户端信息
            ip_address, user_agent = self._get_client_info(request)
            
            # 根据操作类型调用相应的服务方法
            if operation_type == 'mute':
                result = UserModerationService.modify_mute_duration(
                    user_id=user_id,
                    new_duration=new_duration,
                    reason=reason,
                    operator_id=request.user.id,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            else:  # ban
                result = UserModerationService.modify_ban_duration(
                    user_id=user_id,
                    new_duration=new_duration,
                    reason=reason,
                    operator_id=request.user.id,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            
            logger.info(
                "修改时长成功: operator=%s, user_id=%s, type=%s, new_duration=%s",
                request.user.username, user_id, operation_type, new_duration
            )
            
            return Response({
                'code': 2000,
                'msg': '修改时长成功',
                'data': result
            }, status=status.HTTP_200_OK)
            
        except Users.DoesNotExist:
            return Response({
                'code': 4004,
                'msg': '用户不存在',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)
        except PermissionError as e:
            return Response({
                'code': 4003,
                'msg': str(e),
                'data': None
            }, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            return Response({
                'code': 4000,
                'msg': str(e),
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("修改时长操作失败: %s", str(e))
            return Response({
                'code': 5000,
                'msg': f'操作失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(methods=['POST'], detail=False, url_path='batch-mute')
    def batch_mute(self, request: Request) -> Response:
        """批量禁言
        
        POST /api/content/moderation/batch-mute/
        
        请求参数：
            user_ids (list): 用户ID列表（最多20个）
            duration (str): 时长
            reason (str): 禁言原因
            
        Returns:
            Response: 批量操作结果
        """
        try:
            # 获取请求参数
            user_ids = request.data.get('user_ids', [])
            duration = request.data.get('duration')
            reason = request.data.get('reason')
            
            # 参数验证
            if not user_ids:
                return Response({
                    'code': 4000,
                    'msg': '用户ID列表不能为空',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not isinstance(user_ids, list):
                return Response({
                    'code': 4000,
                    'msg': '用户ID列表格式错误',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not duration:
                return Response({
                    'code': 4000,
                    'msg': '时长不能为空',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not reason:
                return Response({
                    'code': 4000,
                    'msg': '禁言原因不能为空',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取客户端信息
            ip_address, user_agent = self._get_client_info(request)
            
            # 调用服务层执行批量禁言
            result = UserModerationService.batch_mute(
                user_ids=user_ids,
                duration=duration,
                reason=reason,
                operator_id=request.user.id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(
                "批量禁言成功: operator=%s, user_count=%s, success=%s, failed=%s",
                request.user.username, result['total'], 
                result['success_count'], result['failed_count']
            )
            
            return Response({
                'code': 2000,
                'msg': '批量禁言成功',
                'data': result
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({
                'code': 4000,
                'msg': str(e),
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("批量禁言操作失败: %s", str(e))
            return Response({
                'code': 5000,
                'msg': f'操作失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(methods=['POST'], detail=False, url_path='batch-ban')
    def batch_ban(self, request: Request) -> Response:
        """批量封禁
        
        POST /api/content/moderation/batch-ban/
        
        请求参数：
            user_ids (list): 用户ID列表（最多20个）
            duration (str): 时长
            reason (str): 封禁原因
            
        Returns:
            Response: 批量操作结果
        """
        try:
            # 获取请求参数
            user_ids = request.data.get('user_ids', [])
            duration = request.data.get('duration')
            reason = request.data.get('reason')
            
            # 参数验证
            if not user_ids:
                return Response({
                    'code': 4000,
                    'msg': '用户ID列表不能为空',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not isinstance(user_ids, list):
                return Response({
                    'code': 4000,
                    'msg': '用户ID列表格式错误',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not duration:
                return Response({
                    'code': 4000,
                    'msg': '时长不能为空',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not reason:
                return Response({
                    'code': 4000,
                    'msg': '封禁原因不能为空',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取客户端信息
            ip_address, user_agent = self._get_client_info(request)
            
            # 调用服务层执行批量封禁
            result = UserModerationService.batch_ban(
                user_ids=user_ids,
                duration=duration,
                reason=reason,
                operator_id=request.user.id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(
                "批量封禁成功: operator=%s, user_count=%s, success=%s, failed=%s",
                request.user.username, result['total'], 
                result['success_count'], result['failed_count']
            )
            
            return Response({
                'code': 2000,
                'msg': '批量封禁成功',
                'data': result
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({
                'code': 4000,
                'msg': str(e),
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("批量封禁操作失败: %s", str(e))
            return Response({
                'code': 5000,
                'msg': f'操作失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(methods=['POST'], detail=False, url_path='batch-unmute')
    def batch_unmute(self, request: Request) -> Response:
        """批量解除禁言
        
        POST /api/content/moderation/batch-unmute/
        
        请求参数：
            user_ids (list): 用户ID列表（最多20个）
            reason (str, 可选): 解除原因
            
        Returns:
            Response: 批量操作结果
        """
        try:
            # 获取请求参数
            user_ids = request.data.get('user_ids', [])
            reason = request.data.get('reason')
            
            # 参数验证
            if not user_ids:
                return Response({
                    'code': 4000,
                    'msg': '用户ID列表不能为空',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not isinstance(user_ids, list):
                return Response({
                    'code': 4000,
                    'msg': '用户ID列表格式错误',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取客户端信息
            ip_address, user_agent = self._get_client_info(request)
            
            # 调用服务层执行批量解除禁言
            result = UserModerationService.batch_unmute(
                user_ids=user_ids,
                operator_id=request.user.id,
                reason=reason,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(
                "批量解除禁言成功: operator=%s, user_count=%s, success=%s, failed=%s",
                request.user.username, result['total'], 
                result['success_count'], result['failed_count']
            )
            
            return Response({
                'code': 2000,
                'msg': '批量解除禁言成功',
                'data': result
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({
                'code': 4000,
                'msg': str(e),
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("批量解除禁言操作失败: %s", str(e))
            return Response({
                'code': 5000,
                'msg': f'操作失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(methods=['POST'], detail=False, url_path='batch-unban')
    def batch_unban(self, request: Request) -> Response:
        """批量解除封禁
        
        POST /api/content/moderation/batch-unban/
        
        请求参数：
            user_ids (list): 用户ID列表（最多20个）
            reason (str, 可选): 解除原因
            
        Returns:
            Response: 批量操作结果
        """
        try:
            # 获取请求参数
            user_ids = request.data.get('user_ids', [])
            reason = request.data.get('reason')
            
            # 参数验证
            if not user_ids:
                return Response({
                    'code': 4000,
                    'msg': '用户ID列表不能为空',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not isinstance(user_ids, list):
                return Response({
                    'code': 4000,
                    'msg': '用户ID列表格式错误',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取客户端信息
            ip_address, user_agent = self._get_client_info(request)
            
            # 调用服务层执行批量解除封禁
            result = UserModerationService.batch_unban(
                user_ids=user_ids,
                operator_id=request.user.id,
                reason=reason,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(
                "批量解除封禁成功: operator=%s, user_count=%s, success=%s, failed=%s",
                request.user.username, result['total'], 
                result['success_count'], result['failed_count']
            )
            
            return Response({
                'code': 2000,
                'msg': '批量解除封禁成功',
                'data': result
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({
                'code': 4000,
                'msg': str(e),
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("批量解除封禁操作失败: %s", str(e))
            return Response({
                'code': 5000,
                'msg': f'操作失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    @action(methods=['GET'], detail=False, url_path='mute-list')
    def mute_list(self, request: Request) -> Response:
        """禁言列表
        
        GET /api/content/moderation/mute-list/
        
        查询参数：
            page (int): 页码，默认1
            page_size (int): 每页数量，默认20
            username (str): 用户名筛选（模糊匹配）
            user_id (int): 用户ID筛选（精确匹配）
            status (str): 状态筛选（active/inactive）
            mute_type (str): 类型筛选（manual/auto）
            operator_id (int): 操作人ID筛选
            start_date (str): 开始日期（YYYY-MM-DD）
            end_date (str): 结束日期（YYYY-MM-DD）
            is_permanent (bool): 是否永久禁言
            
        Returns:
            Response: 禁言列表数据
        """
        try:
            # 获取查询参数
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            username = request.query_params.get('username')
            user_id = request.query_params.get('user_id')
            status_filter = request.query_params.get('status')
            mute_type = request.query_params.get('mute_type')
            operator_id = request.query_params.get('operator_id')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            is_permanent = request.query_params.get('is_permanent')
            
            # 构建查询
            queryset = UserMuteRecord.objects.select_related(
                'user', 'muted_by', 'unmuted_by'
            ).all()
            
            # 应用筛选条件
            if username:
                queryset = queryset.filter(user__username__icontains=username)
            
            if user_id:
                queryset = queryset.filter(user_id=user_id)
            
            if status_filter == 'active':
                queryset = queryset.filter(is_active=True)
            elif status_filter == 'inactive':
                queryset = queryset.filter(is_active=False)
            
            if mute_type:
                queryset = queryset.filter(mute_type=mute_type)
            
            if operator_id:
                queryset = queryset.filter(muted_by_id=operator_id)
            
            if start_date:
                queryset = queryset.filter(create_datetime__gte=start_date)
            
            if end_date:
                queryset = queryset.filter(create_datetime__lte=end_date)
            
            if is_permanent is not None:
                if is_permanent in ['true', 'True', '1', True]:
                    queryset = queryset.filter(muted_until__isnull=True)
                else:
                    queryset = queryset.filter(muted_until__isnull=False)
            
            # 按创建时间倒序排列
            queryset = queryset.order_by('-create_datetime')
            
            # 计算总数
            total = queryset.count()
            
            # 分页
            start = (page - 1) * page_size
            end = start + page_size
            records = queryset[start:end]
            
            # 序列化结果
            results = []
            for record in records:
                # 计算剩余时长
                remaining = DurationFormatter.format_remaining(record.muted_until)
                
                result_item = {
                    'id': record.id,
                    'user': {
                        'id': record.user.id,
                        'username': record.user.username,
                        'avatar': getattr(record.user, 'avatar', '')
                    },
                    'mute_type': record.mute_type,
                    'muted_by': {
                        'id': record.muted_by.id,
                        'username': record.muted_by.username
                    } if record.muted_by else None,
                    'mute_reason': record.mute_reason,
                    'muted_at': record.create_datetime.isoformat() if record.create_datetime else None,
                    'muted_until': record.muted_until.isoformat() if record.muted_until else None,
                    'remaining': remaining,
                    'is_active': record.is_active,
                    'is_manually_modified': record.is_manually_modified,
                    'unmuted_at': record.unmuted_at.isoformat() if record.unmuted_at else None,
                    'unmuted_by': {
                        'id': record.unmuted_by.id,
                        'username': record.unmuted_by.username
                    } if record.unmuted_by else None,
                    'unmute_reason': record.unmute_reason
                }
                results.append(result_item)
            
            return Response({
                'code': 2000,
                'msg': '查询成功',
                'data': {
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'results': results
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception("查询禁言列表失败: %s", str(e))
            return Response({
                'code': 5000,
                'msg': f'查询失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(methods=['GET'], detail=False, url_path='ban-list')
    def ban_list(self, request: Request) -> Response:
        """封禁列表
        
        GET /api/content/moderation/ban-list/
        
        查询参数：
            page (int): 页码，默认1
            page_size (int): 每页数量，默认20
            username (str): 用户名筛选（模糊匹配）
            user_id (int): 用户ID筛选（精确匹配）
            status (str): 状态筛选（active/inactive）
            start_date (str): 开始日期（YYYY-MM-DD）
            end_date (str): 结束日期（YYYY-MM-DD）
            is_permanent (bool): 是否永久封禁
            
        Returns:
            Response: 封禁列表数据
        """
        try:
            # 获取查询参数
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            username = request.query_params.get('username')
            user_id = request.query_params.get('user_id')
            status_filter = request.query_params.get('status')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            is_permanent = request.query_params.get('is_permanent')
            
            # 构建查询 - 查询封禁用户（is_active=False）
            queryset = Users.objects.filter(is_active=False)
            
            # 应用筛选条件
            if username:
                queryset = queryset.filter(username__icontains=username)
            
            if user_id:
                queryset = queryset.filter(id=user_id)
            
            # 状态筛选：active表示封禁中，inactive表示已解除
            # 这里通过locked_until判断
            if status_filter == 'active':
                # 封禁中：locked_until为None（永久）或大于当前时间
                queryset = queryset.filter(
                    Q(locked_until__isnull=True) | Q(locked_until__gt=datetime.now())
                )
            elif status_filter == 'inactive':
                # 已过期：locked_until小于等于当前时间
                queryset = queryset.filter(
                    locked_until__isnull=False,
                    locked_until__lte=datetime.now()
                )
            
            if is_permanent is not None:
                if is_permanent in ['true', 'True', '1', True]:
                    queryset = queryset.filter(locked_until__isnull=True)
                else:
                    queryset = queryset.filter(locked_until__isnull=False)
            
            # 按更新时间倒序排列
            queryset = queryset.order_by('-update_datetime')
            
            # 计算总数
            total = queryset.count()
            
            # 分页
            start = (page - 1) * page_size
            end = start + page_size
            users = queryset[start:end]
            
            # 序列化结果
            results = []
            for user in users:
                # 计算剩余时长
                remaining = DurationFormatter.format_remaining(user.locked_until)
                
                # 查询最近的封禁日志获取操作人信息
                ban_log = UserModerationLog.objects.filter(
                    target_user_id=user.id,
                    operation_type='ban'
                ).select_related('operator').order_by('-create_datetime').first()
                
                result_item = {
                    'id': user.id,
                    'username': user.username,
                    'avatar': getattr(user, 'avatar', ''),
                    'ban_reason': user.ban_reason,
                    'locked_until': user.locked_until.isoformat() if user.locked_until else None,
                    'remaining': remaining,
                    'is_active': user.is_active,
                    'banned_at': ban_log.create_datetime.isoformat() if ban_log else None,
                    'banned_by': {
                        'id': ban_log.operator.id,
                        'username': ban_log.operator.username
                    } if ban_log and ban_log.operator else None
                }
                results.append(result_item)
            
            return Response({
                'code': 2000,
                'msg': '查询成功',
                'data': {
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'results': results
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception("查询封禁列表失败: %s", str(e))
            return Response({
                'code': 5000,
                'msg': f'查询失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(methods=['GET'], detail=False, url_path='auto-mute-list')
    def auto_mute_list(self, request: Request) -> Response:
        """AI自动禁言列表
        
        GET /api/content/moderation/auto-mute-list/
        
        查询参数：
            page (int): 页码，默认1
            page_size (int): 每页数量，默认20
            username (str): 用户名筛选（模糊匹配）
            status (str): 状态筛选（active/inactive/modified）
            
        Returns:
            Response: AI自动禁言列表数据
        """
        try:
            # 获取查询参数
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            username = request.query_params.get('username')
            status_filter = request.query_params.get('status')
            
            # 构建查询 - 仅查询AI自动禁言记录
            queryset = UserMuteRecord.objects.select_related(
                'user'
            ).filter(mute_type='auto')
            
            # 应用筛选条件
            if username:
                queryset = queryset.filter(user__username__icontains=username)
            
            if status_filter == 'active':
                queryset = queryset.filter(is_active=True, is_manually_modified=False)
            elif status_filter == 'inactive':
                queryset = queryset.filter(is_active=False)
            elif status_filter == 'modified':
                queryset = queryset.filter(is_manually_modified=True)
            
            # 按创建时间倒序排列
            queryset = queryset.order_by('-create_datetime')
            
            # 计算总数
            total = queryset.count()
            
            # 分页
            start = (page - 1) * page_size
            end = start + page_size
            records = queryset[start:end]
            
            # 序列化结果
            results = []
            for record in records:
                # 计算剩余时长
                remaining = DurationFormatter.format_remaining(record.muted_until)
                
                # 确定自动解封状态
                if record.is_manually_modified:
                    auto_unmute_status = 'modified'  # 已被人工修改
                elif not record.is_active:
                    auto_unmute_status = 'completed'  # 已解封
                else:
                    auto_unmute_status = 'pending'  # 等待中
                
                result_item = {
                    'id': record.id,
                    'user': {
                        'id': record.user.id,
                        'username': record.user.username,
                        'avatar': getattr(record.user, 'avatar', '')
                    },
                    'mute_type': record.mute_type,
                    'mute_reason': record.mute_reason,
                    'muted_at': record.create_datetime.isoformat() if record.create_datetime else None,
                    'muted_until': record.muted_until.isoformat() if record.muted_until else None,
                    'remaining': remaining,
                    'is_active': record.is_active,
                    'is_manually_modified': record.is_manually_modified,
                    'auto_unmute_task_id': record.auto_unmute_task_id,
                    'auto_unmute_status': auto_unmute_status
                }
                results.append(result_item)
            
            return Response({
                'code': 2000,
                'msg': '查询成功',
                'data': {
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'results': results
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception("查询AI自动禁言列表失败: %s", str(e))
            return Response({
                'code': 5000,
                'msg': f'查询失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(methods=['GET'], detail=False)
    def logs(self, request: Request) -> Response:
        """操作日志
        
        GET /api/content/moderation/logs/
        
        查询参数：
            page (int): 页码，默认1
            page_size (int): 每页数量，默认20
            operator_id (int): 操作人ID筛选
            target_user_id (int): 目标用户ID筛选
            operation_type (str): 操作类型筛选
            start_date (str): 开始日期（YYYY-MM-DD）
            end_date (str): 结束日期（YYYY-MM-DD）
            
        Returns:
            Response: 操作日志数据
        """
        try:
            # 获取查询参数
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            operator_id = request.query_params.get('operator_id')
            target_user_id = request.query_params.get('target_user_id')
            operation_type = request.query_params.get('operation_type')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            # 构建查询
            queryset = UserModerationLog.objects.select_related(
                'operator', 'target_user'
            ).all()
            
            # 应用筛选条件
            if operator_id:
                queryset = queryset.filter(operator_id=operator_id)
            
            if target_user_id:
                queryset = queryset.filter(target_user_id=target_user_id)
            
            if operation_type:
                queryset = queryset.filter(operation_type=operation_type)
            
            if start_date:
                queryset = queryset.filter(create_datetime__gte=start_date)
            
            if end_date:
                queryset = queryset.filter(create_datetime__lte=end_date)
            
            # 按创建时间倒序排列
            queryset = queryset.order_by('-create_datetime')
            
            # 计算总数
            total = queryset.count()
            
            # 分页
            start = (page - 1) * page_size
            end = start + page_size
            logs = queryset[start:end]
            
            # 序列化结果
            results = []
            for log in logs:
                # 格式化时长显示
                duration_display = DurationFormatter.format_hours(log.duration_hours)
                old_duration_display = DurationFormatter.format_hours(log.old_duration_hours) if log.old_duration_hours else None
                
                result_item = {
                    'id': log.id,
                    'operator': {
                        'id': log.operator.id,
                        'username': log.operator.username
                    },
                    'target_user': {
                        'id': log.target_user.id,
                        'username': log.target_user.username
                    },
                    'operation_type': log.operation_type,
                    'reason': log.reason,
                    'duration_hours': log.duration_hours,
                    'duration_display': duration_display,
                    'old_duration_hours': log.old_duration_hours,
                    'old_duration_display': old_duration_display,
                    'ip_address': log.ip_address,
                    'user_agent': log.user_agent,
                    'extra_data': log.extra_data,
                    'created_at': log.create_datetime.isoformat() if log.create_datetime else None
                }
                results.append(result_item)
            
            return Response({
                'code': 2000,
                'msg': '查询成功',
                'data': {
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'results': results
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception("查询操作日志失败: %s", str(e))
            return Response({
                'code': 5000,
                'msg': f'查询失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(methods=['GET'], detail=False)
    def export(self, request: Request) -> Response:
        """导出数据
        
        GET /api/content/moderation/export/
        
        查询参数：
            type (str): 导出类型（mute/ban/auto_mute）
            format (str): 导出格式（csv/excel）
            其他筛选参数同列表查询
            
        Returns:
            HttpResponse: 文件下载响应
        """
        try:
            # 获取导出参数
            export_type = request.query_params.get('type')
            export_format = request.query_params.get('format', 'csv')
            
            # 参数验证
            if not export_type or export_type not in ['mute', 'ban', 'auto_mute']:
                return Response({
                    'code': 4000,
                    'msg': '导出类型必须是mute、ban或auto_mute',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if export_format not in ['csv', 'excel']:
                return Response({
                    'code': 4000,
                    'msg': '导出格式必须是csv或excel',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 根据类型查询数据
            if export_type == 'mute':
                queryset = UserMuteRecord.objects.select_related(
                    'user', 'muted_by', 'unmuted_by'
                ).all()
                
                # 应用筛选条件（复用mute_list的筛选逻辑）
                username = request.query_params.get('username')
                if username:
                    queryset = queryset.filter(user__username__icontains=username)
                
                # 其他筛选条件...
                
                queryset = queryset.order_by('-create_datetime')
                
            elif export_type == 'auto_mute':
                queryset = UserMuteRecord.objects.select_related(
                    'user'
                ).filter(mute_type='auto')
                
                username = request.query_params.get('username')
                if username:
                    queryset = queryset.filter(user__username__icontains=username)
                
                queryset = queryset.order_by('-create_datetime')
                
            else:  # ban
                queryset = Users.objects.filter(is_active=False)
                
                username = request.query_params.get('username')
                if username:
                    queryset = queryset.filter(username__icontains=username)
                
                queryset = queryset.order_by('-update_datetime')
            
            # 生成文件
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if export_format == 'csv':
                # 生成CSV文件
                response = HttpResponse(content_type='text/csv; charset=utf-8')
                response['Content-Disposition'] = f'attachment; filename="{export_type}_export_{timestamp}.csv"'
                
                # 添加BOM以支持Excel正确显示中文
                response.write('\ufeff')
                
                writer = csv.writer(response)
                
                # 写入表头
                if export_type in ['mute', 'auto_mute']:
                    writer.writerow([
                        '用户ID', '用户名', '禁言类型', '禁言原因', 
                        '禁言时间', '截止时间', '状态', '操作人'
                    ])
                    
                    # 写入数据
                    for record in queryset:
                        writer.writerow([
                            record.user.id,
                            record.user.username,
                            '手动禁言' if record.mute_type == 'manual' else 'AI自动禁言',
                            record.mute_reason,
                            record.create_datetime.strftime('%Y-%m-%d %H:%M:%S') if record.create_datetime else '',
                            record.muted_until.strftime('%Y-%m-%d %H:%M:%S') if record.muted_until else '永久',
                            '禁言中' if record.is_active else '已解除',
                            record.muted_by.username if record.muted_by else '系统'
                        ])
                else:  # ban
                    writer.writerow([
                        '用户ID', '用户名', '封禁原因', '截止时间', '状态'
                    ])
                    
                    for user in queryset:
                        writer.writerow([
                            user.id,
                            user.username,
                            user.ban_reason or '',
                            user.locked_until.strftime('%Y-%m-%d %H:%M:%S') if user.locked_until else '永久',
                            '封禁中' if not user.is_active else '已解除'
                        ])
                
                logger.info(
                    "导出数据成功: operator=%s, type=%s, format=%s, count=%s",
                    request.user.username, export_type, export_format, queryset.count()
                )
                
                return response
                
            else:  # excel
                # 生成Excel文件（使用openpyxl）
                try:
                    from openpyxl import Workbook
                    
                    wb = Workbook()
                    ws = wb.active
                    ws.title = f"{export_type}_export"
                    
                    # 写入表头
                    if export_type in ['mute', 'auto_mute']:
                        ws.append([
                            '用户ID', '用户名', '禁言类型', '禁言原因', 
                            '禁言时间', '截止时间', '状态', '操作人'
                        ])
                        
                        # 写入数据
                        for record in queryset:
                            ws.append([
                                record.user.id,
                                record.user.username,
                                '手动禁言' if record.mute_type == 'manual' else 'AI自动禁言',
                                record.mute_reason,
                                record.create_datetime.strftime('%Y-%m-%d %H:%M:%S') if record.create_datetime else '',
                                record.muted_until.strftime('%Y-%m-%d %H:%M:%S') if record.muted_until else '永久',
                                '禁言中' if record.is_active else '已解除',
                                record.muted_by.username if record.muted_by else '系统'
                            ])
                    else:  # ban
                        ws.append([
                            '用户ID', '用户名', '封禁原因', '截止时间', '状态'
                        ])
                        
                        for user in queryset:
                            ws.append([
                                user.id,
                                user.username,
                                user.ban_reason or '',
                                user.locked_until.strftime('%Y-%m-%d %H:%M:%S') if user.locked_until else '永久',
                                '封禁中' if not user.is_active else '已解除'
                            ])
                    
                    # 保存到BytesIO
                    output = BytesIO()
                    wb.save(output)
                    output.seek(0)
                    
                    response = HttpResponse(
                        output.read(),
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    response['Content-Disposition'] = f'attachment; filename="{export_type}_export_{timestamp}.xlsx"'
                    
                    logger.info(
                        "导出数据成功: operator=%s, type=%s, format=%s, count=%s",
                        request.user.username, export_type, export_format, queryset.count()
                    )
                    
                    return response
                    
                except ImportError:
                    return Response({
                        'code': 5000,
                        'msg': 'Excel导出功能需要安装openpyxl库',
                        'data': None
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            logger.exception("导出数据失败: %s", str(e))
            return Response({
                'code': 5000,
                'msg': f'导出失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

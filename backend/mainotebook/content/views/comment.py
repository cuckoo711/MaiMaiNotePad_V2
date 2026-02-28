# -*- coding: utf-8 -*-

"""
评论视图集

提供评论的 CRUD 操作和点赞功能。
支持嵌套回复和树形结构返回。
"""

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone

from mainotebook.utils.viewset import CustomModelViewSet
from mainotebook.content.models import Comment
from mainotebook.content.serializers.comment import (
    CommentSerializer,
    CommentCreateSerializer
)
from mainotebook.content.services.comment_service import CommentService
from mainotebook.content.permissions import CanComment, IsAdminUser


class CommentViewSet(CustomModelViewSet):
    """评论视图集
    
    提供评论的 CRUD 操作和点赞功能。
    支持嵌套回复和树形结构返回。
    
    API 端点：
    - GET /api/content/comments/ - 获取评论列表
    - POST /api/content/comments/ - 发表评论
    - DELETE /api/content/comments/{id}/ - 删除评论（软删除）
    - POST /api/content/comments/{id}/like/ - 点赞评论
    - DELETE /api/content/comments/{id}/like/ - 取消点赞评论
    - POST /api/content/comments/{id}/restore/ - 恢复评论（管理员）
    - GET /api/content/comments/admin_list/ - 管理后台评论列表（含已删除）
    - POST /api/content/comments/{id}/ban_user/ - 封禁评论用户（管理员）
    - POST /api/content/comments/{id}/admin_delete/ - 管理后台删除评论（管理员）
    """
    
    queryset = Comment.objects.filter(is_deleted=False)
    serializer_class = CommentSerializer
    create_serializer_class = CommentCreateSerializer
    ordering_fields = ['create_datetime', 'like_count']
    # 前台内容接口不使用后台数据级权限过滤，避免无部门用户查不到数据
    extra_filter_class = []
    
    def get_permissions(self):
        """根据操作类型返回不同的权限要求
        
        Returns:
            list: 权限类列表
        """
        if self.action in ['create']:
            # 创建评论需要认证且未被禁言
            return [IsAuthenticated(), CanComment()]
        elif self.action in ['restore']:
            # 恢复评论需要管理员权限
            return [IsAuthenticated(), IsAdminUser()]
        elif self.action in ['destroy', 'like', 'unlike', 'react']:
            # 删除、点赞、取消点赞需要认证
            return [IsAuthenticated()]
        else:
            # 列表和详情查看不需要权限
            return []
    
    def list(self, request, *args, **kwargs):
        """获取评论列表
        
        支持按 target_id 和 target_type 筛选，返回树形结构。
        
        Query Parameters:
            target_id (str): 目标 ID（必需）
            target_type (str): 目标类型（'knowledge' 或 'persona'，必需）
            
        Returns:
            Response: 评论树形结构列表
        """
        # 获取查询参数
        target_id = request.query_params.get('target_id')
        target_type = request.query_params.get('target_type')
        
        # 验证必需参数
        if not target_id or not target_type:
            return Response(
                {
                    'code': 4000,
                    'msg': '缺少必需参数 target_id 或 target_type'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 验证 target_type 的有效性
        if target_type not in ['knowledge', 'persona']:
            return Response(
                {
                    'code': 4000,
                    'msg': 'target_type 必须是 knowledge 或 persona'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 使用服务层获取评论树形结构
        try:
            root_comments = CommentService.get_comments_tree(target_id, target_type)
            
            # 序列化评论
            serializer = self.get_serializer(root_comments, many=True)
            
            return Response(
                {
                    'code': 2000,
                    'msg': '获取成功',
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    'code': 5000,
                    'msg': f'获取评论列表失败: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def create(self, request, *args, **kwargs):
        """发表评论
        
        创建新评论或回复。验证用户禁言状态和父评论有效性。
        
        Request Body:
            target_id (str): 目标 ID
            target_type (str): 目标类型（'knowledge' 或 'persona'）
            content (str): 评论内容（不超过 500 字符）
            parent (uuid, optional): 父评论 ID（回复时提供）
            
        Returns:
            Response: 创建的评论对象
        """
        # 使用创建序列化器验证数据
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            
            # 保存评论（序列化器会自动设置 user）
            comment = serializer.save()
            
            # 使用展示序列化器返回数据
            response_serializer = CommentSerializer(comment, context={'request': request})
            
            return Response(
                {
                    'code': 2000,
                    'msg': '评论发表成功',
                    'data': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return Response(
                {
                    'code': 4000,
                    'msg': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'code': 5000,
                    'msg': f'发表评论失败: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """删除评论（软删除）
        
        软删除评论及其所有子评论。只有评论创建者或管理员可以删除。
        
        Path Parameters:
            pk (uuid): 评论 ID
            
        Returns:
            Response: 删除成功消息
        """
        try:
            # 获取评论对象
            comment = self.get_object()
            
            # 使用服务层删除评论
            CommentService.delete_comment(comment, request.user)
            
            return Response(
                {
                    'code': 2000,
                    'msg': '评论删除成功'
                },
                status=status.HTTP_200_OK
            )
        except PermissionDenied as e:
            return Response(
                {
                    'code': 4003,
                    'msg': str(e)
                },
                status=status.HTTP_403_FORBIDDEN
            )
        except Comment.DoesNotExist:
            return Response(
                {
                    'code': 4004,
                    'msg': '评论不存在'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {
                    'code': 5000,
                    'msg': f'删除评论失败: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(methods=['POST'], detail=True, url_path='react')
    def react(self, request, pk=None):
        """评论反应（点赞/点踩/取消）
        
        统一处理用户对评论的反应操作。
        
        Path Parameters:
            pk (uuid): 评论 ID
            
        Request Body:
            action (str): 操作类型，'like'、'dislike' 或 'clear'
            
        Returns:
            Response: 操作结果，包含 like_count、dislike_count、my_reaction
        """
        try:
            comment = self.get_object()
            react_action = request.data.get('action')
            
            if react_action not in ('like', 'dislike', 'clear'):
                return Response(
                    {
                        'code': 4000,
                        'msg': '无效的操作类型，仅支持 like、dislike、clear'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = CommentService.react_comment(comment, request.user, react_action)
            
            msg_map = {
                'like': '点赞成功',
                'dislike': '点踩成功',
                'clear': '已取消',
            }
            
            return Response(
                {
                    'code': 2000,
                    'msg': msg_map.get(react_action, '操作成功'),
                    'data': result
                },
                status=status.HTTP_200_OK
            )
        except Comment.DoesNotExist:
            return Response(
                {
                    'code': 4004,
                    'msg': '评论不存在'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {
                    'code': 5000,
                    'msg': f'操作失败: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(methods=['POST'], detail=True, url_path='like')
    def like(self, request, pk=None):
        """点赞评论（兼容旧接口）
        
        Path Parameters:
            pk (uuid): 评论 ID
            
        Returns:
            Response: 点赞成功消息和更新后的计数
        """
        try:
            comment = self.get_object()
            result = CommentService.react_comment(comment, request.user, 'like')
            return Response(
                {
                    'code': 2000,
                    'msg': '点赞成功',
                    'data': result
                },
                status=status.HTTP_200_OK
            )
        except Comment.DoesNotExist:
            return Response(
                {'code': 4004, 'msg': '评论不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'code': 5000, 'msg': f'点赞失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(methods=['DELETE'], detail=True, url_path='like')
    def unlike(self, request, pk=None):
        """取消点赞评论（兼容旧接口）
        
        Path Parameters:
            pk (uuid): 评论 ID
            
        Returns:
            Response: 取消点赞成功消息和更新后的计数
        """
        try:
            comment = self.get_object()
            result = CommentService.react_comment(comment, request.user, 'clear')
            return Response(
                {
                    'code': 2000,
                    'msg': '取消点赞成功',
                    'data': result
                },
                status=status.HTTP_200_OK
            )
        except Comment.DoesNotExist:
            return Response(
                {'code': 4004, 'msg': '评论不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'code': 5000, 'msg': f'取消点赞失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(methods=['POST'], detail=True, url_path='restore')
    def restore(self, request, pk=None):
        """恢复已删除的评论（管理员）
        
        恢复已被软删除的评论的可见状态。只有管理员可以执行此操作。
        
        Path Parameters:
            pk (uuid): 评论 ID
            
        Returns:
            Response: 恢复成功消息
        """
        try:
            # 获取评论对象（包括已删除的）
            comment = Comment.objects.get(pk=pk)
            
            # 检查评论是否已被删除
            if not comment.is_deleted:
                return Response(
                    {
                        'code': 4000,
                        'msg': '评论未被删除，无需恢复'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 恢复评论
            comment.is_deleted = False
            comment.save()
            
            return Response(
                {
                    'code': 2000,
                    'msg': '评论恢复成功'
                },
                status=status.HTTP_200_OK
            )
        except Comment.DoesNotExist:
            return Response(
                {
                    'code': 4004,
                    'msg': '评论不存在'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {
                    'code': 5000,
                    'msg': f'恢复评论失败: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(methods=['GET'], detail=False, url_path='admin_list')
    def admin_list(self, request):
        """管理后台评论列表（包含已删除的评论）
        
        返回所有评论（含已删除），支持分页和筛选。
        仅管理员可访问。
        
        Query Parameters:
            target_type (str): 目标类型筛选
            is_deleted (bool): 删除状态筛选
            content (str): 内容模糊搜索
            user (int): 用户 ID 筛选
            page (int): 页码
            limit (int): 每页数量
            
        Returns:
            Response: 分页评论列表
        """
        # 查询所有评论（包含已删除的）
        queryset = Comment.objects.all().select_related('user').order_by('-create_datetime')
        
        # 按目标类型筛选
        target_type = request.query_params.get('target_type')
        if target_type:
            queryset = queryset.filter(target_type=target_type)
        
        # 按删除状态筛选
        is_deleted = request.query_params.get('is_deleted')
        if is_deleted is not None and is_deleted != '':
            queryset = queryset.filter(is_deleted=is_deleted in ['true', 'True', '1'])
        
        # 按内容模糊搜索
        content = request.query_params.get('content')
        if content:
            queryset = queryset.filter(content__icontains=content)
        
        # 按用户筛选
        user_id = request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # 按评论层级筛选（是否为一级评论）
        is_root = request.query_params.get('is_root')
        if is_root is not None and is_root != '':
            if is_root in ['true', 'True', '1']:
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent__isnull=False)
        
        # 分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = CommentSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = CommentSerializer(queryset, many=True, context={'request': request})
        return Response(
            {
                'code': 2000,
                'msg': '获取成功',
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )
    
    @action(methods=['POST'], detail=True, url_path='admin_delete')
    def admin_delete(self, request, pk=None):
        """管理后台删除评论（软删除，含级联逻辑）
        
        管理员删除评论：
        - 一级评论（无父评论）：连带软删除所有子评论
        - 二级评论（有父评论）：仅软删除该评论本身，不连带删除回复
        
        Path Parameters:
            pk (uuid): 评论 ID
            
        Returns:
            Response: 删除成功消息
        """
        try:
            # 获取评论对象（包含已删除的，以便管理员操作）
            comment = Comment.objects.get(pk=pk)
            
            if comment.is_deleted:
                return Response(
                    {'code': 4000, 'msg': '该评论已被删除'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 判断评论层级
            if comment.parent is None:
                # 一级评论：连带软删除所有子评论
                child_count = comment.replies.filter(is_deleted=False).count()
                comment.replies.filter(is_deleted=False).update(is_deleted=True)
                comment.is_deleted = True
                comment.save()
                msg = f'删除成功，同时删除了 {child_count} 条子评论'
            else:
                # 二级评论：仅删除自身
                comment.is_deleted = True
                comment.save()
                msg = '删除成功'
            
            return Response(
                {'code': 2000, 'msg': msg},
                status=status.HTTP_200_OK
            )
        except Comment.DoesNotExist:
            return Response(
                {'code': 4004, 'msg': '评论不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'code': 5000, 'msg': f'删除评论失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(methods=['POST'], detail=True, url_path='ban_user')
    def ban_user(self, request, pk=None):
        """封禁评论用户（管理员）
        
        对指定评论的用户进行禁言处理。
        
        Path Parameters:
            pk (uuid): 评论 ID
            
        Request Body:
            reason (str): 封禁原因（必填）
            duration_hours (int, optional): 封禁时长（小时），不传则永久封禁
            
        Returns:
            Response: 封禁成功消息
        """
        try:
            comment = Comment.objects.select_related('user').get(pk=pk)
            user = comment.user
            
            reason = request.data.get('reason', '')
            if not reason:
                return Response(
                    {'code': 4000, 'msg': '封禁原因为必填项'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            duration_hours = request.data.get('duration_hours')
            
            # 设置禁言
            user.is_muted = True
            user.mute_reason = reason
            
            if duration_hours:
                # 定时封禁
                user.muted_until = timezone.now() + timezone.timedelta(hours=int(duration_hours))
            else:
                # 永久封禁（muted_until 为 None 表示永久）
                user.muted_until = None
            
            user.save()
            
            duration_text = f'{duration_hours} 小时' if duration_hours else '永久'
            return Response(
                {
                    'code': 2000,
                    'msg': f'已封禁用户 {user.username}（{duration_text}）',
                    'data': {
                        'user_id': user.id,
                        'username': user.username,
                        'is_muted': user.is_muted,
                        'muted_until': str(user.muted_until) if user.muted_until else None,
                        'mute_reason': user.mute_reason,
                    }
                },
                status=status.HTTP_200_OK
            )
        except Comment.DoesNotExist:
            return Response(
                {'code': 4004, 'msg': '评论不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'code': 5000, 'msg': f'封禁用户失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

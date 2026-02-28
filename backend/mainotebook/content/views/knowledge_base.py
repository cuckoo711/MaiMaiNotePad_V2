# -*- coding: utf-8 -*-

"""
知识库视图集

提供知识库的 CRUD 操作和文件管理功能。
"""

from django.db import models
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from mainotebook.utils.json_response import DetailResponse, ErrorResponse
from mainotebook.utils.viewset import CustomModelViewSet
from mainotebook.content.models import KnowledgeBase, KnowledgeBaseFile
from mainotebook.content.serializers.knowledge_base import (
    KnowledgeBaseSerializer,
    KnowledgeBaseCreateSerializer,
    KnowledgeBaseUpdateSerializer,
    KnowledgeBaseFileSerializer
)
from mainotebook.content.filters import KnowledgeBaseFilter
from mainotebook.content.permissions import IsOwnerOrReadOnly
from mainotebook.content.services.knowledge_base_service import KnowledgeBaseService
from mainotebook.content.services.file_service import FileService
from mainotebook.content.services.star_service import StarService

import logging

logger = logging.getLogger(__name__)


class KnowledgeBaseViewSet(CustomModelViewSet):
    """知识库视图集
    
    提供知识库的 CRUD 操作和文件管理功能。
    
    标准操作：
    - list: 获取公开知识库列表（已审核通过的公开内容）
    - retrieve: 获取知识库详情
    - create: 创建知识库
    - update: 更新知识库
    - destroy: 删除知识库（软删除）
    
    自定义操作：
    - my: 获取当前用户的知识库列表
    - files: 添加文件到知识库
    - delete_file: 从知识库删除文件
    - download_file: 下载知识库文件
    - submit: 提交知识库审核
    - star: 收藏知识库
    - unstar: 取消收藏知识库
    """
    
    queryset = KnowledgeBase.objects.all()
    serializer_class = KnowledgeBaseSerializer
    create_serializer_class = KnowledgeBaseCreateSerializer
    update_serializer_class = KnowledgeBaseUpdateSerializer
    filter_class = KnowledgeBaseFilter
    search_fields = ['name', 'description', 'tags']
    ordering_fields = ['create_datetime', 'update_datetime', 'name', 'star_count', 'downloads']
    ordering = ['-create_datetime']
    # 前台内容接口不使用后台数据级权限过滤，避免无部门用户查不到数据
    extra_filter_class = []
    
    def get_permissions(self):
        """根据操作类型返回不同的权限类
        
        Returns:
            list: 权限类列表
        """
        if self.action in ['create', 'my', 'files', 'delete_file', 'download_file', 'submit', 'star', 'unstar']:
            # 需要认证的操作
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # 需要认证且仅创建者可操作
            return [IsAuthenticated(), IsOwnerOrReadOnly()]
        else:
            # list 和 retrieve 允许所有人访问
            return []
    
    def get_queryset(self):
        """根据操作类型返回不同的查询集
        
        - list: 只返回公开且已审核的知识库
        - retrieve/file_detail: 管理员/审核员可查看所有，普通用户只能看公开内容和自己的
        - 其他操作: 返回所有知识库
        
        Returns:
            QuerySet: 知识库查询集
        """
        if self.action == 'list':
            return KnowledgeBase.objects.filter(
                is_public=True,
                is_pending=False
            )
        if self.action in ('retrieve', 'file_detail'):
            user = self.request.user
            if user and user.is_authenticated:
                if user.is_superuser or user.is_staff or getattr(user, 'is_moderator', False):
                    return KnowledgeBase.objects.all()
                return KnowledgeBase.objects.filter(
                    models.Q(is_public=True, is_pending=False) | models.Q(uploader=user)
                )
            return KnowledgeBase.objects.filter(is_public=True, is_pending=False)
        return KnowledgeBase.objects.all()
    
    def perform_create(self, serializer):
        """创建知识库后处理上传的文件，公开内容自动触发 AI 审核

        Args:
            serializer: 知识库创建序列化器
        """
        knowledge_base = serializer.save()

        # 处理上传的文件
        files = self.request.FILES.getlist('files')
        for file in files:
            is_valid, error_msg = FileService.validate_file(file)
            if not is_valid:
                logger.warning(f"创建知识库时文件验证失败: {file.name}, {error_msg}")
                continue

            upload_path = f'knowledge_base/{knowledge_base.id}'
            file_info = FileService.save_file(file, upload_path)
            KnowledgeBaseFile.objects.create(
                knowledge_base=knowledge_base,
                **file_info
            )
            logger.info(
                f"用户 {self.request.user.id} 创建知识库 {knowledge_base.id} "
                f"时上传文件: {file_info['original_name']}"
            )
        
        # 公开内容自动触发 AI 审核
        if knowledge_base.is_public and knowledge_base.is_pending:
            from mainotebook.content.tasks import auto_review_task
            auto_review_task.delay(str(knowledge_base.id), 'knowledge')
            logger.info(f"知识库 {knowledge_base.id} 已触发 AI 自动审核")
    
    @swagger_auto_schema(
        operation_summary='获取当前用户的知识库列表',
        operation_description='返回当前用户创建的所有知识库（包括草稿、待审核、已发布、已拒绝）',
        responses={200: KnowledgeBaseSerializer(many=True)}
    )
    @action(methods=['GET'], detail=False, permission_classes=[IsAuthenticated])
    def my(self, request):
        """获取当前用户的知识库列表
        
        Args:
            request: HTTP 请求对象
            
        Returns:
            Response: 包含用户知识库列表的响应
        """
        queryset = KnowledgeBaseService.get_user_knowledge_bases(request.user)
        
        # 应用分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return DetailResponse(data=serializer.data, msg="获取成功")
    
    @swagger_auto_schema(
        operation_summary='添加文件到知识库',
        operation_description='上传文件并关联到指定的知识库',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['file'],
            properties={
                'file': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description='要上传的文件'
                )
            }
        ),
        responses={
            200: KnowledgeBaseFileSerializer(),
            400: '文件验证失败',
            403: '无权限操作',
            404: '知识库不存在'
        }
    )
    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    def files(self, request, pk=None):
        """添加文件到知识库
        
        Args:
            request: HTTP 请求对象
            pk: 知识库 ID
            
        Returns:
            Response: 包含文件信息的响应
        """
        knowledge_base = self.get_object()
        
        # 验证权限（仅创建者可添加文件）
        if knowledge_base.uploader != request.user:
            return ErrorResponse(msg="只有创建者可以添加文件", status=status.HTTP_403_FORBIDDEN)
        
        # 获取上传的文件
        file = request.FILES.get('file')
        if not file:
            return ErrorResponse(msg="未找到上传的文件", status=status.HTTP_400_BAD_REQUEST)
        
        # 验证文件
        is_valid, error_msg = FileService.validate_file(file)
        if not is_valid:
            return ErrorResponse(msg=error_msg, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 保存文件
            upload_path = f'knowledge_base/{pk}'
            file_info = FileService.save_file(file, upload_path)
            
            # 创建文件记录
            kb_file = KnowledgeBaseFile.objects.create(
                knowledge_base=knowledge_base,
                **file_info
            )
            
            # 序列化并返回
            serializer = KnowledgeBaseFileSerializer(kb_file)
            return DetailResponse(data=serializer.data, msg="文件上传成功")
            
        except Exception as e:
            return ErrorResponse(msg=f"文件上传失败: {str(e)}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(
        methods=['GET', 'DELETE'],
        detail=True,
        url_path='files/(?P<file_id>[^/.]+)',
        permission_classes=[IsAuthenticated]
    )
    def file_detail(self, request, pk=None, file_id=None):
        """获取或删除知识库文件
        
        GET: 下载文件
        DELETE: 删除文件
        
        Args:
            request: HTTP 请求对象
            pk: 知识库 ID
            file_id: 文件 ID
            
        Returns:
            FileResponse/Response: 文件下载响应或删除成功响应
        """
        knowledge_base = self.get_object()
        
        # 获取文件记录
        try:
            kb_file = KnowledgeBaseFile.objects.get(
                id=file_id,
                knowledge_base=knowledge_base
            )
        except KnowledgeBaseFile.DoesNotExist:
            return ErrorResponse(msg="文件不存在", status=status.HTTP_404_NOT_FOUND)
        
        if request.method == 'DELETE':
            # 验证权限（仅创建者可删除文件）
            if knowledge_base.uploader != request.user:
                return ErrorResponse(msg="只有创建者可以删除文件", status=status.HTTP_403_FORBIDDEN)
            
            FileService.delete_file(kb_file.file_path)
            kb_file.delete()
            return DetailResponse(data=[], msg="文件删除成功")
        
        # GET: 下载文件
        try:
            return FileService.get_file_response(kb_file.file_path, kb_file.original_name)
        except FileNotFoundError:
            return ErrorResponse(msg="文件不存在", status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return ErrorResponse(msg=f"文件下载失败: {str(e)}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_summary='提交知识库审核',
        operation_description='将知识库提交审核，审核通过后将公开显示',
        responses={
            200: '提交成功',
            400: '状态不允许提交',
            403: '无权限操作',
            404: '知识库不存在'
        }
    )
    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    def submit(self, request, pk=None):
        """提交知识库审核
        
        Args:
            request: HTTP 请求对象
            pk: 知识库 ID
            
        Returns:
            Response: 提交结果响应
        """
        knowledge_base = self.get_object()
        
        try:
            # 调用服务层方法提交审核
            KnowledgeBaseService.submit_for_review(knowledge_base, request.user)
            return DetailResponse(data=[], msg="提交审核成功")
            
        except PermissionError as e:
            return ErrorResponse(msg=str(e), status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return ErrorResponse(msg=str(e), status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_summary='收藏知识库',
        operation_description='将知识库添加到用户的收藏列表',
        responses={
            200: '收藏成功',
            400: '已收藏或内容不存在',
            404: '知识库不存在'
        }
    )
    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    def star(self, request, pk=None):
        """收藏知识库
        
        Args:
            request: HTTP 请求对象
            pk: 知识库 ID
            
        Returns:
            Response: 收藏结果响应
        """
        knowledge_base = self.get_object()
        
        try:
            # 调用服务层方法收藏
            StarService.star_content(request.user, str(knowledge_base.id), 'knowledge')
            return DetailResponse(data=[], msg="收藏成功")
            
        except Exception as e:
            return ErrorResponse(msg=str(e), status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_summary='取消收藏知识库',
        operation_description='从用户的收藏列表中移除知识库',
        responses={
            200: '取消收藏成功',
            404: '知识库不存在'
        }
    )
    @action(methods=['DELETE'], detail=True, permission_classes=[IsAuthenticated])
    def unstar(self, request, pk=None):
        """取消收藏知识库
        
        Args:
            request: HTTP 请求对象
            pk: 知识库 ID
            
        Returns:
            Response: 取消收藏结果响应
        """
        knowledge_base = self.get_object()
        
        try:
            # 调用服务层方法取消收藏
            StarService.unstar_content(request.user, str(knowledge_base.id), 'knowledge')
            return DetailResponse(data=[], msg="取消收藏成功")
            
        except Exception as e:
            return ErrorResponse(msg=str(e), status=status.HTTP_400_BAD_REQUEST)

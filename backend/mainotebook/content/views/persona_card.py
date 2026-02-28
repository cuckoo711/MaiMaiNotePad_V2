# -*- coding: utf-8 -*-

"""
人设卡视图集

提供人设卡的 CRUD 操作和文件管理功能。
依赖框架的 CustomModelViewSet 统一响应格式和 CustomExceptionHandler 统一异常处理。
"""

import logging
import toml
from typing import Any, Optional
from django.db import models
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import PermissionDenied

from mainotebook.utils.viewset import CustomModelViewSet
from mainotebook.utils.json_response import DetailResponse, ErrorResponse
from mainotebook.content.models import PersonaCard, PersonaCardFile
from mainotebook.content.serializers.persona_card import (
    PersonaCardSerializer,
    PersonaCardCreateSerializer,
    PersonaCardUpdateSerializer,
    PersonaCardFileSerializer
)
from mainotebook.content.filters import PersonaCardFilter
from mainotebook.content.permissions import IsOwnerOrReadOnly
from mainotebook.content.services.persona_card_service import PersonaCardService
from mainotebook.content.services.file_service import FileService
from mainotebook.content.services.star_service import StarService

logger = logging.getLogger(__name__)


class PersonaCardViewSet(CustomModelViewSet):
    """人设卡视图集
    
    提供人设卡的 CRUD 操作和文件管理功能。
    
    标准 CRUD 操作直接继承 CustomModelViewSet，由框架统一处理响应格式和异常。
    自定义 action 使用 DetailResponse/ErrorResponse 保持一致。
    """
    
    queryset = PersonaCard.objects.all()
    serializer_class = PersonaCardSerializer
    create_serializer_class = PersonaCardCreateSerializer
    update_serializer_class = PersonaCardUpdateSerializer
    filter_class = PersonaCardFilter
    search_fields = ['name', 'description', 'tags']
    ordering_fields = ['create_datetime', 'update_datetime', 'name', 'star_count', 'downloads']
    ordering = ['-create_datetime']
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    # 前台内容接口不使用后台数据级权限过滤，避免无部门用户查不到数据
    extra_filter_class = []

    def get_queryset(self):
        """获取查询集
        
        - list: 只返回公开且已审核的人设卡
        - retrieve/file_detail: 管理员/审核员可查看所有，普通用户只能看公开内容和自己的
        - 其他操作: 返回所有人设卡
        
        Returns:
            QuerySet: 人设卡查询集
        """
        queryset = super().get_queryset()
        if self.action == 'list':
            queryset = queryset.filter(is_public=True, is_pending=False)
        elif self.action in ('retrieve', 'file_detail'):
            user = self.request.user
            if user and user.is_authenticated:
                # 超级管理员、管理员、审核员可查看所有内容
                if user.is_superuser or user.is_staff or getattr(user, 'is_moderator', False):
                    pass  # 不过滤
                else:
                    # 普通用户只能看公开内容和自己创建的
                    queryset = queryset.filter(
                        models.Q(is_public=True, is_pending=False) | models.Q(uploader=user)
                    )
            else:
                queryset = queryset.filter(is_public=True, is_pending=False)
        return queryset
    
    def perform_create(self, serializer):
        """创建人设卡后处理上传的文件，解析版本号，触发 AI 审核
        
        Args:
            serializer: 人设卡创建序列化器
        """
        persona_card = serializer.save()
        
        # 处理上传的文件
        toml_file_record = None
        files = self.request.FILES.getlist('files')
        for file in files:
            is_valid, error_msg = FileService.validate_file(file)
            if not is_valid:
                logger.warning(f"创建人设卡时文件验证失败: {file.name}, {error_msg}")
                continue
            
            upload_path = f'persona_cards/{persona_card.id}'
            file_info = FileService.save_file(file, upload_path)
            pc_file = PersonaCardFile.objects.create(
                persona_card=persona_card,
                **file_info
            )
            logger.info(
                f"用户 {self.request.user.id} 创建人设卡 {persona_card.id} "
                f"时上传文件: {file_info['original_name']}"
            )
            # 记录 bot_config.toml 文件用于版本解析
            if file_info['original_name'] == 'bot_config.toml':
                toml_file_record = pc_file
        
        # 从 bot_config.toml 解析版本号
        if toml_file_record:
            version = self._parse_version_from_toml(toml_file_record.file_path)
            if version:
                persona_card.version = version
                persona_card.save(update_fields=['version'])
                logger.info(
                    f"人设卡 {persona_card.id} 从 bot_config.toml 解析到版本号: {version}"
                )
        
        # 公开内容自动触发 AI 审核
        if persona_card.is_public and persona_card.is_pending:
            from mainotebook.content.tasks import auto_review_task
            auto_review_task.delay(str(persona_card.id), 'persona')
            logger.info(f"人设卡 {persona_card.id} 已触发 AI 自动审核")
    
    @staticmethod
    def _parse_version_from_toml(file_path: str) -> Optional[str]:
        """从 bot_config.toml 文件中解析版本号
        
        按优先级搜索：顶层字段 → meta/card 子字段 → 深度搜索。
        
        Args:
            file_path: toml 文件路径
            
        Returns:
            Optional[str]: 版本号，未找到返回 None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = toml.load(f)
        except Exception as e:
            logger.warning(f"读取 bot_config.toml 失败: {file_path}, 错误: {e}")
            return None
        
        if not isinstance(data, dict):
            return None
        
        # 1. 顶层字段
        for key in ('version', 'Version', 'schema_version', 'card_version'):
            value = data.get(key)
            if isinstance(value, (str, int, float)):
                return str(value)
        
        # 2. meta/card 子字段
        for meta_key in ('meta', 'Meta', 'card', 'Card'):
            meta = data.get(meta_key)
            if isinstance(meta, dict):
                for key in ('version', 'Version', 'schema_version', 'card_version'):
                    value = meta.get(key)
                    if isinstance(value, (str, int, float)):
                        return str(value)
        
        # 3. 深度搜索
        return PersonaCardViewSet._deep_search_version(data)
    
    @staticmethod
    def _deep_search_version(data: dict) -> Optional[str]:
        """深度搜索版本字段
        
        Args:
            data: 字典数据
            
        Returns:
            Optional[str]: 版本号，未找到返回 None
        """
        visited = set()
        stack: list[Any] = [data]
        while stack:
            current = stack.pop()
            if id(current) in visited:
                continue
            visited.add(id(current))
            if isinstance(current, dict):
                for k, v in current.items():
                    if isinstance(k, str) and k.lower() == 'version' and isinstance(v, (str, int, float)):
                        return str(v)
                    if isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(current, list):
                for item in current:
                    if isinstance(item, (dict, list)):
                        stack.append(item)
        return None
    
    def destroy(self, request, *args, **kwargs):
        """删除人设卡
        
        使用服务层处理关联数据清理（收藏记录等）。
        
        Args:
            request: HTTP 请求对象
            
        Returns:
            Response: 删除成功响应
        """
        instance = self.get_object()
        PersonaCardService.delete_persona_card(instance, request.user)
        return DetailResponse(data=[], msg='删除成功')
    
    @action(methods=['GET'], detail=False, url_path='my')
    def my(self, request):
        """获取当前用户的人设卡列表
        
        Args:
            request: HTTP 请求对象
            
        Returns:
            Response: 用户的人设卡列表响应
        """
        queryset = PersonaCardService.get_user_persona_cards(request.user)
        
        # 支持按名称搜索
        name = request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)
        
        # 应用分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return DetailResponse(data=serializer.data, msg='获取成功')
    
    @action(methods=['POST'], detail=True, url_path='files')
    def files(self, request, pk=None):
        """添加文件到人设卡
        
        Args:
            request: HTTP 请求对象，包含上传的文件
            pk: 人设卡 ID
            
        Returns:
            Response: 文件信息响应
        """
        persona_card = self.get_object()
        
        if persona_card.uploader != request.user:
            return ErrorResponse(msg='只有创建者可以添加文件', code=403)
        
        file = request.FILES.get('file')
        if not file:
            return ErrorResponse(msg='请上传文件')
        
        # 验证文件
        is_valid, error_msg = FileService.validate_file(file)
        if not is_valid:
            return ErrorResponse(msg=error_msg)
        
        # 保存文件
        upload_path = f'persona_cards/{persona_card.id}'
        file_info = FileService.save_file(file, upload_path)
        
        persona_card_file = PersonaCardFile.objects.create(
            persona_card=persona_card,
            **file_info
        )
        
        logger.info(
            f"用户 {request.user.id} 为人设卡 {persona_card.id} "
            f"添加文件: {file_info['original_name']}"
        )
        
        serializer = PersonaCardFileSerializer(persona_card_file)
        return DetailResponse(data=serializer.data, msg='文件添加成功')

    @action(
        methods=['GET', 'DELETE'],
        detail=True,
        url_path='files/(?P<file_id>[^/.]+)'
    )
    def file_detail(self, request, pk=None, file_id=None):
        """获取或删除人设卡文件
        
        GET: 下载文件
        DELETE: 删除文件
        
        Args:
            request: HTTP 请求对象
            pk: 人设卡 ID
            file_id: 文件 ID
            
        Returns:
            FileResponse/Response: 文件下载响应或删除成功响应
        """
        persona_card = self.get_object()
        
        try:
            persona_card_file = PersonaCardFile.objects.get(
                id=file_id,
                persona_card=persona_card
            )
        except PersonaCardFile.DoesNotExist:
            return ErrorResponse(msg='文件不存在', code=404)
        
        if request.method == 'DELETE':
            if persona_card.uploader != request.user:
                return ErrorResponse(msg='只有创建者可以删除文件', code=403)
            
            FileService.delete_file(persona_card_file.file_path)
            persona_card_file.delete()
            
            logger.info(
                f"用户 {request.user.id} 从人设卡 {persona_card.id} "
                f"删除文件: {persona_card_file.original_name}"
            )
            return DetailResponse(data=[], msg='删除成功')
        
        # GET: 下载文件
        persona_card.downloads += 1
        persona_card.save(update_fields=['downloads'])
        
        logger.info(
            f"用户 {request.user.id} 下载人设卡 {persona_card.id} "
            f"的文件: {persona_card_file.original_name}"
        )
        
        return FileService.get_file_response(
            persona_card_file.file_path,
            persona_card_file.original_name
        )
    
    @action(methods=['POST'], detail=True, url_path='submit')
    def submit(self, request, pk=None):
        """提交人设卡审核
        
        Args:
            request: HTTP 请求对象
            pk: 人设卡 ID
            
        Returns:
            Response: 提交成功响应
        """
        persona_card = self.get_object()
        PersonaCardService.submit_for_review(persona_card, request.user)
        
        logger.info(
            f"用户 {request.user.id} 提交人设卡审核: {persona_card.id}"
        )
        
        return DetailResponse(data=[], msg='提交审核成功')
    
    @action(methods=['POST'], detail=True, url_path='star')
    def star(self, request, pk=None):
        """收藏人设卡
        
        Args:
            request: HTTP 请求对象
            pk: 人设卡 ID
            
        Returns:
            Response: 收藏成功响应
        """
        persona_card = self.get_object()
        
        StarService.star_content(
            request.user,
            str(persona_card.id),
            'persona'
        )
        
        logger.info(
            f"用户 {request.user.id} 收藏人设卡: {persona_card.id}"
        )
        
        return DetailResponse(data=[], msg='收藏成功')
    
    @action(methods=['DELETE'], detail=True, url_path='star')
    def unstar(self, request, pk=None):
        """取消收藏人设卡
        
        Args:
            request: HTTP 请求对象
            pk: 人设卡 ID
            
        Returns:
            Response: 取消收藏成功响应
        """
        persona_card = self.get_object()
        
        StarService.unstar_content(
            request.user,
            str(persona_card.id),
            'persona'
        )
        
        logger.info(
            f"用户 {request.user.id} 取消收藏人设卡: {persona_card.id}"
        )
        
        return DetailResponse(data=[], msg='取消收藏成功')

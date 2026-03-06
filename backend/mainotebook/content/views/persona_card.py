# -*- coding: utf-8 -*-

"""
人设卡视图集

提供人设卡的 CRUD 操作和文件管理功能。
依赖框架的 CustomModelViewSet 统一响应格式和 CustomExceptionHandler 统一异常处理。
"""

import logging
import os
import toml
from typing import Any, Optional
from django.db import models
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import PermissionDenied
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

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
from mainotebook.content.services.file_validation_service import FileValidationService
from mainotebook.content.services.toml_parser_service import TomlParserService
from mainotebook.content.services.sensitive_info_detector_service import SensitiveInfoDetectorService
from mainotebook.content.services.captcha_service import CaptchaService
from mainotebook.content.services.upload_quota_service import UploadQuotaService
from mainotebook.content.services.persona_card_config_service import PersonaCardConfigService

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
    # 数据权限过滤：普通用户只能看到自己的内容，管理员和审核员可以看到所有内容
    # extra_filter_class 留空，在 get_queryset 中根据用户角色动态过滤
    extra_filter_class = []
    
    def get_permissions(self):
        """根据操作类型返回不同的权限类
        
        Returns:
            list: 权限类列表
        """
        if self.action in ['create', 'my', 'files', 'file_detail', 'submit', 'star', 'unstar']:
            # 需要认证的操作
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # 需要认证且仅创建者可操作
            return [IsAuthenticated(), IsOwnerOrReadOnly()]
        else:
            # list 和 retrieve 允许所有人访问
            return []

    def get_queryset(self):
        """根据操作类型和用户角色返回不同的查询集（任务 16.2）
        
        权限规则：
        - 超级管理员/管理员/审核员：可查看所有内容
        - 普通用户：
          - list（广场）: 只能看公开且已审核的内容
          - my（内容管理）: 只能看自己创建的内容
          - retrieve/file_detail: 可查看公开内容和自己的内容
        - 已删除的人设卡对其他用户不可见（需求 12.10）
        
        Returns:
            QuerySet: 人设卡查询集
        """
        user = self.request.user
        
        # 判断用户角色
        is_admin_or_reviewer = False
        if user and user.is_authenticated:
            # 超级管理员或职员
            if user.is_superuser or user.is_staff:
                is_admin_or_reviewer = True
            else:
                # 检查是否为审核员角色
                user_roles = user.role.all()
                role_keys = [role.key for role in user_roles]
                if 'admin' in role_keys or 'reviewer' in role_keys:
                    is_admin_or_reviewer = True
        
        # list 操作（广场）：只返回公开且已审核且未删除的人设卡
        if self.action == 'list':
            queryset = PersonaCard.objects.filter(
                is_public=True,
                is_pending=False,
                is_deleted=False  # 过滤已删除的人设卡
            )
            
            # 处理收藏筛选
            starred_param = self.request.query_params.get('starred', '').lower()
            if starred_param == 'true' and user.is_authenticated:
                # 只返回当前用户收藏的人设卡
                from mainotebook.content.models import StarRecord
                import uuid as uuid_module
                
                # 获取收藏的 target_id（字符串格式）
                starred_id_strs = StarRecord.objects.filter(
                    user=user,
                    target_type='persona'
                ).values_list('target_id', flat=True)
                
                # 将字符串转换为 UUID 对象
                starred_ids = []
                for id_str in starred_id_strs:
                    try:
                        starred_ids.append(uuid_module.UUID(id_str))
                    except (ValueError, AttributeError):
                        continue
                
                queryset = queryset.filter(id__in=starred_ids)
                
            return queryset
        
        # retrieve/file_detail 操作：查看详情
        if self.action in ('retrieve', 'file_detail'):
            if user and user.is_authenticated:
                # 管理员/审核员可查看所有（包括已删除的）
                if is_admin_or_reviewer:
                    return PersonaCard.objects.all()
                # 普通用户只能看公开内容（未删除）和自己的（包括已删除）
                return PersonaCard.objects.filter(
                    models.Q(is_public=True, is_pending=False, is_deleted=False) | 
                    models.Q(uploader=user)  # 上传者可以看到自己的所有人设卡，包括已删除的
                )
            # 未登录用户只能看公开且未删除的内容
            return PersonaCard.objects.filter(is_public=True, is_pending=False, is_deleted=False)
        
        # 其他操作（create/update/delete/files 等）
        # 管理员/审核员可操作所有
        if is_admin_or_reviewer:
            return PersonaCard.objects.all()
        
        # 普通用户只能操作自己的（包括已删除的，以便查看）
        if user and user.is_authenticated:
            return PersonaCard.objects.filter(uploader=user)
        
        # 未登录用户返回空查询集
        return PersonaCard.objects.none()
    
    def perform_create(self, serializer):
        """创建人设卡后处理上传的文件，解析版本号，用户选择公开时自动提交审核

        创建流程统一为：先创建私有人设卡 → 处理文件 → 解析版本号 → 如果用户选择了
        公开则调用 submit_for_review 走统一审核流程，确保审核入口唯一，避免重复通知。

        Args:
            serializer: 人设卡创建序列化器
        """
        # 记录用户是否选择了公开（serializer 已将 is_public 统一设为 False）
        want_public = str(self.request.data.get('is_public', '')).lower() == 'true'

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
        
        # 用户选择公开时，通过 submit_for_review 统一走审核流程
        if want_public:
            try:
                from mainotebook.content.services.persona_card_service import PersonaCardService
                PersonaCardService.submit_for_review(
                    persona_card, self.request.user
                )
                logger.info(f"人设卡 {persona_card.id} 创建时选择公开，已提交审核")
            except Exception as e:
                logger.warning(
                    f"人设卡 {persona_card.id} 创建时自动提交审核失败: {e}"
                )
    
    @staticmethod
    def _parse_version_from_toml(file_path: str) -> Optional[str]:
        """从 bot_config.toml 文件中解析版本号
        
        按优先级搜索：顶层字段 → meta/card 子字段 → 深度搜索。
        
        Args:
            file_path: toml 文件路径（相对于 MEDIA_ROOT）
            
        Returns:
            Optional[str]: 版本号，未找到返回 None
        """
        try:
            from django.conf import settings
            full_path = os.path.join(settings.MEDIA_ROOT, file_path)
            with open(full_path, 'r', encoding='utf-8') as f:
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
        
        # 2. meta/card/inner 子字段
        for meta_key in ('inner', 'Inner', 'meta', 'Meta', 'card', 'Card'):
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
        """删除人设卡（软删除）（任务 16.2）
        
        实现软删除：设置 is_deleted=True 而不是物理删除。
        已删除的人设卡对其他用户不可见，但保留在数据库中。
        
        需求：12.8, 12.9, 12.10
        Bug 修复：标签统计生命周期同步 - 需求 2.1
        
        Args:
            request: HTTP 请求对象
            
        Returns:
            Response: 删除成功响应
        """
        # 直接获取对象，不使用 get_queryset 过滤
        try:
            instance = PersonaCard.objects.get(pk=kwargs.get('pk'))
        except PersonaCard.DoesNotExist:
            return ErrorResponse(msg='人设卡不存在', code=404)
        
        # 检查用户权限（只有上传者可以删除）
        if instance.uploader != request.user:
            logger.warning(
                f"用户 {request.user.id} 尝试删除非自己的人设卡: "
                f"persona_card_id={instance.id}, uploader_id={instance.uploader_id}"
            )
            return ErrorResponse(msg='只有上传者可以删除人设卡', code=403, status=403)
        
        # 在软删除前检查 is_public 状态和标签
        # 注意：这些变量目前未使用，但保留以便将来可能需要
        was_public = instance.is_public
        tags = instance.tags if was_public else None
        
        # 软删除：设置 is_deleted=True
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])
        
        # 注意：标签统计的更新由 pre_save 信号处理器自动处理
        logger.info(
            f"人设卡 {instance.id} 已软删除, user_id={request.user.id}"
        )
        
        return DetailResponse(data=[], msg='删除成功')
    
    def perform_update(self, serializer):
        """更新人设卡后处理
        
        标签统计的同步由 pre_save 信号处理器自动处理。
        
        Args:
            serializer: 人设卡更新序列化器
        """
        # 保存更新（pre_save 信号会自动处理标签统计同步）
        serializer.save()
    
    @action(methods=['GET'], detail=False, url_path='my')
    def my(self, request):
        """获取当前用户的人设卡列表
        
        Args:
            request: HTTP 请求对象
            
        Returns:
            Response: 用户的人设卡列表响应
        """
        queryset = PersonaCardService.get_user_persona_cards(request.user)
        
        # 支持按名称搜索（兼容 name 和 keyword 参数）
        keyword = request.query_params.get('keyword') or request.query_params.get('name')
        if keyword:
            queryset = queryset.filter(name__icontains=keyword)
        
        # 支持按公开状态筛选
        is_public = request.query_params.get('is_public')
        if is_public is not None:
            is_public_bool = is_public.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_public=is_public_bool)
        
        # 支持按审核状态筛选
        is_pending = request.query_params.get('is_pending')
        if is_pending is not None:
            is_pending_bool = is_pending.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_pending=is_pending_bool)
        
        # 支持排序
        ordering = request.query_params.get('ordering')
        if ordering:
            queryset = queryset.order_by(ordering)
        
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
    
    @action(
        methods=['GET'],
        detail=True,
        url_path='files/(?P<file_id>[^/.]+)/parse'
    )
    def parse_toml(self, request, pk=None, file_id=None):
        """解析 TOML 文件并返回结构化数据
        
        将 TOML 文件解析为结构化的 JSON 数据，包含：
        - 原始文本内容
        - 解析后的块（sections）和键值对
        - 每个键值对的类型信息
        
        Args:
            request: HTTP 请求对象
            pk: 人设卡 ID
            file_id: 文件 ID
            
        Returns:
            Response: 包含解析结果的响应
        """
        persona_card = self.get_object()
        
        try:
            persona_card_file = PersonaCardFile.objects.get(
                id=file_id,
                persona_card=persona_card
            )
        except PersonaCardFile.DoesNotExist:
            return ErrorResponse(msg='文件不存在', code=404)
        
        # 检查文件类型
        if not persona_card_file.original_name.lower().endswith('.toml'):
            return ErrorResponse(msg='只支持解析 TOML 文件')
        
        try:
            from django.conf import settings
            full_path = os.path.join(settings.MEDIA_ROOT, persona_card_file.file_path)
            
            # 读取原始文本
            with open(full_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
            
            # 解析 TOML
            with open(full_path, 'r', encoding='utf-8') as f:
                toml_data = toml.load(f)
            
            # 构建结构化数据
            parsed_data = {
                'raw_content': raw_content,
                'blocks': self._parse_toml_structure(toml_data)
            }
            
            logger.info(
                f"用户 {request.user.id if request.user.is_authenticated else '匿名'} "
                f"解析人设卡 {persona_card.id} 的 TOML 文件: {persona_card_file.original_name}"
            )
            
            return DetailResponse(data=parsed_data, msg='解析成功')
            
        except toml.TomlDecodeError as e:
            logger.warning(f"TOML 解析失败: {persona_card_file.file_path}, 错误: {e}")
            return ErrorResponse(msg=f'TOML 格式错误: {str(e)}')
        except Exception as e:
            logger.error(f"解析 TOML 文件失败: {persona_card_file.file_path}, 错误: {e}")
            return ErrorResponse(msg=f'解析失败: {str(e)}')
    
    @staticmethod
    def _parse_toml_structure(data: dict, parent_key: str = '') -> list:
        """将 TOML 数据解析为结构化的块列表
        
        Args:
            data: TOML 解析后的字典数据
            parent_key: 父级键名（用于嵌套表）
            
        Returns:
            list: 块列表，每个块包含标题和键值对
        """
        blocks = []
        root_block = None
        
        for key, value in data.items():
            full_key = f"{parent_key}.{key}" if parent_key else key
            
            if isinstance(value, dict):
                # 嵌套表，创建一个新块
                block = {
                    'title': full_key,
                    'key_values': []
                }
                
                # 递归处理嵌套字典
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, dict):
                        # 继续递归
                        nested_blocks = PersonaCardViewSet._parse_toml_structure(
                            {sub_key: sub_value}, full_key
                        )
                        blocks.extend(nested_blocks)
                    else:
                        # 添加键值对
                        block['key_values'].append({
                            'key': sub_key,
                            'value': sub_value,
                            'type': PersonaCardViewSet._get_value_type(sub_value)
                        })
                
                if block['key_values']:
                    blocks.append(block)
            else:
                # 顶层键值对，放入根块
                if root_block is None:
                    root_block = {
                        'title': parent_key if parent_key else '根配置',
                        'key_values': []
                    }
                
                root_block['key_values'].append({
                    'key': key,
                    'value': value,
                    'type': PersonaCardViewSet._get_value_type(value)
                })
        
        # 将根块放在最前面
        if root_block and root_block['key_values']:
            blocks.insert(0, root_block)
        
        return blocks
    
    @staticmethod
    def _get_value_type(value: Any) -> str:
        """获取值的类型
        
        Args:
            value: 值
            
        Returns:
            str: 类型名称
        """
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, str):
            if '\n' in value:
                return 'multiline_string'
            return 'string'
        elif isinstance(value, list):
            return 'array'
        elif isinstance(value, dict):
            return 'table'
        else:
            return 'unknown'
    
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
    
    @action(methods=['DELETE'], detail=True)
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
    
    @swagger_auto_schema(
        operation_summary='解析上传的 TOML 文件',
        operation_description='''
        接收 bot_config.toml 文件上传，验证文件格式和大小，解析 TOML 内容，检测敏感信息。
        此端点不创建数据库记录，只返回解析结果供前端使用。
        
        文件要求：
        - 文件名必须为 bot_config.toml
        - 文件大小：1KB - 2MB
        - MIME 类型：text/plain 或 application/toml
        - 编码：UTF-8
        - 必须包含 version 字段
        ''',
        manual_parameters=[
            openapi.Parameter(
                'file',
                openapi.IN_FORM,
                description='bot_config.toml 文件',
                type=openapi.TYPE_FILE,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description='解析成功',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='状态码'),
                        'msg': openapi.Schema(type=openapi.TYPE_STRING, description='消息'),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'sections': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    description='配置块列表',
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'name': openapi.Schema(type=openapi.TYPE_STRING, description='配置块名称'),
                                            'comment': openapi.Schema(type=openapi.TYPE_STRING, description='配置块注释'),
                                            'items': openapi.Schema(
                                                type=openapi.TYPE_ARRAY,
                                                description='配置项列表',
                                                items=openapi.Schema(
                                                    type=openapi.TYPE_OBJECT,
                                                    properties={
                                                        'key': openapi.Schema(type=openapi.TYPE_STRING, description='配置键名'),
                                                        'value': openapi.Schema(type=openapi.TYPE_STRING, description='配置值'),
                                                        'type': openapi.Schema(type=openapi.TYPE_STRING, description='数据类型'),
                                                        'comment': openapi.Schema(type=openapi.TYPE_STRING, description='配置项注释')
                                                    }
                                                )
                                            )
                                        }
                                    )
                                ),
                                'version': openapi.Schema(type=openapi.TYPE_STRING, description='版本号'),
                                'sensitive_info': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    description='检测到的敏感信息列表',
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'section': openapi.Schema(type=openapi.TYPE_STRING, description='配置块名称'),
                                            'key': openapi.Schema(type=openapi.TYPE_STRING, description='配置键名'),
                                            'value': openapi.Schema(type=openapi.TYPE_STRING, description='包含敏感信息的值'),
                                            'matches': openapi.Schema(
                                                type=openapi.TYPE_ARRAY,
                                                description='匹配到的敏感数字',
                                                items=openapi.Schema(type=openapi.TYPE_STRING)
                                            ),
                                            'path': openapi.Schema(type=openapi.TYPE_STRING, description='配置项路径')
                                        }
                                    )
                                )
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(description='文件验证失败或解析失败')
        },
        tags=['人设卡上传']
    )
    @action(methods=['POST'], detail=False, url_path='parse-toml')
    def parse_toml_upload(self, request):
        """解析上传的 TOML 文件（任务 14.1）
        
        接收文件上传，验证文件，解析 TOML 内容，检测敏感信息。
        此端点不创建数据库记录，只返回解析结果。
        
        需求：3.1, 3.2, 3.3, 3.4, 4.1, 8.1, 8.2
        
        Args:
            request: HTTP 请求对象，包含上传的文件
            
        Returns:
            Response: 包含解析结果和敏感信息列表的响应
        """
        # 获取上传的文件
        file = request.FILES.get('file')
        if not file:
            return ErrorResponse(msg='请上传文件', code=400)
        
        # 验证文件
        is_valid, error_msg = FileValidationService.validate_file(file)
        if not is_valid:
            logger.warning(
                f"用户 {request.user.id if request.user.is_authenticated else '匿名'} "
                f"上传文件验证失败: {error_msg}"
            )
            return ErrorResponse(msg=error_msg, code=400)
        
        try:
            # 读取文件内容
            file.seek(0)
            content = file.read().decode('utf-8')
            
            # 解析 TOML
            parsed_data = TomlParserService.parse_content(content)
            
            # 检测敏感信息
            sensitive_items = SensitiveInfoDetectorService.detect_from_sections(
                parsed_data.get('sections', [])
            )
            
            logger.info(
                f"用户 {request.user.id if request.user.is_authenticated else '匿名'} "
                f"解析 TOML 文件成功，检测到 {len(sensitive_items)} 个敏感信息"
            )
            
            return DetailResponse(
                data={
                    'sections': parsed_data.get('sections', []),
                    'version': parsed_data.get('version'),
                    'sensitive_info': sensitive_items
                },
                msg='解析成功'
            )
            
        except ValueError as e:
            # TOML 结构验证错误（如缺少 version 字段）
            logger.warning(
                f"TOML 结构验证失败: {str(e)}"
            )
            return ErrorResponse(msg=str(e), code=400)
        except Exception as e:
            # TOML 解析错误或其他异常
            logger.error(
                f"解析 TOML 文件失败: {str(e)}",
                exc_info=True
            )
            return ErrorResponse(msg=f'解析失败: {str(e)}', code=400)
    
    @swagger_auto_schema(
        operation_summary='创建人设卡及配置',
        operation_description='''
        创建人设卡并保存配置项。支持上传文件、配置敏感信息确认。
        
        功能：
        - 检查用户权限和上传限额（每日最多 10 次）
        - 验证基本信息（名称、描述等）
        - 创建人设卡和配置项
        - 处理文件上传
        - 如果选择公开，自动触发审核流程
        
        上传限额：每个用户每天最多上传 10 个人设卡，UTC 零点重置。
        ''',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['name', 'description', 'configs'],
            properties={
                'name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='人设卡名称（1-200 个字符）',
                    min_length=1,
                    max_length=200
                ),
                'description': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='人设卡描述（至少 10 个字符）',
                    min_length=10
                ),
                'copyright_owner': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='版权所有者（可选，默认为上传者用户名）'
                ),
                'tags': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='标签（可选，多个标签用逗号分隔）'
                ),
                'is_public': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description='是否公开（默认为 false）',
                    default=False
                ),
                'configs': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description='配置项列表',
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'section_name': openapi.Schema(type=openapi.TYPE_STRING, description='配置块名称'),
                            'key_name': openapi.Schema(type=openapi.TYPE_STRING, description='配置键名'),
                            'value': openapi.Schema(type=openapi.TYPE_STRING, description='配置值'),
                            'data_type': openapi.Schema(
                                type=openapi.TYPE_STRING,
                                description='数据类型',
                                enum=['string', 'integer', 'float', 'boolean', 'array', 'object']
                            ),
                            'description': openapi.Schema(type=openapi.TYPE_STRING, description='配置项注释')
                        }
                    )
                ),
                'sensitive_confirmation': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    description='敏感信息确认（如果配置中包含敏感信息）',
                    properties={
                        'text': openapi.Schema(type=openapi.TYPE_STRING, description='确认声明'),
                        'locations': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description='敏感信息位置列表',
                            items=openapi.Schema(type=openapi.TYPE_STRING)
                        )
                    }
                )
            }
        ),
        responses={
            200: openapi.Response(
                description='创建成功',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='状态码'),
                        'msg': openapi.Schema(type=openapi.TYPE_STRING, description='消息'),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_STRING, description='人设卡 ID'),
                                'name': openapi.Schema(type=openapi.TYPE_STRING, description='人设卡名称'),
                                'description': openapi.Schema(type=openapi.TYPE_STRING, description='人设卡描述'),
                                'is_public': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='是否公开'),
                                'is_pending': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='是否待审核')
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(description='数据验证失败'),
            401: openapi.Response(description='用户未认证'),
            403: openapi.Response(description='用户被封禁'),
            429: openapi.Response(description='超过上传限额'),
            500: openapi.Response(description='创建失败')
        },
        tags=['人设卡上传']
    )
    @action(methods=['POST'], detail=False, url_path='create-with-config')
    def create_with_config(self, request):
        """创建人设卡及配置（任务 14.2）
        
        检查用户权限和上传限额，验证请求数据，使用事务创建人设卡、配置项和文件记录。
        如果是公开人设卡，触发审核流程。
        
        需求：1.1, 1.3, 2.1, 2.2, 6.1, 10.1, 10.2
        
        Args:
            request: HTTP 请求对象
            
        Returns:
            Response: 创建成功响应
        """
        from django.db import transaction
        
        # 检查用户权限
        if not request.user.is_authenticated:
            return ErrorResponse(msg='用户未认证', code=401)
        
        # 检查上传权限（未被封禁）
        if hasattr(request.user, 'is_banned') and request.user.is_banned:
            logger.warning(
                f"被封禁用户尝试上传人设卡: user_id={request.user.id}"
            )
            return ErrorResponse(msg='您已被封禁，无法上传人设卡', code=403)
        
        # 检查上传限额
        can_upload, remaining = UploadQuotaService.check_quota(request.user.id)
        if not can_upload:
            logger.warning(
                f"用户超过上传限额: user_id={request.user.id}"
            )
            return ErrorResponse(
                msg=f'您今日的上传次数已达上限（{UploadQuotaService.DAILY_LIMIT} 次），请明天再试',
                code=429
            )
        
        # 验证请求数据
        serializer = PersonaCardCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            logger.warning(
                f"创建人设卡数据验证失败: user_id={request.user.id}, "
                f"errors={serializer.errors}"
            )
            return ErrorResponse(
                msg='数据验证失败',
                data=serializer.errors,
                code=400
            )
        
        try:
            # 使用事务创建人设卡和配置项
            with transaction.atomic():
                # 创建人设卡（序列化器会自动创建配置项和敏感信息确认记录）
                persona_card = serializer.save()
                
                # 处理文件上传
                files = request.FILES.getlist('files')
                for file in files:
                    is_valid, error_msg = FileService.validate_file(file)
                    if not is_valid:
                        logger.warning(
                            f"创建人设卡时文件验证失败: {file.name}, {error_msg}"
                        )
                        continue
                    
                    upload_path = f'persona_cards/{persona_card.id}'
                    file_info = FileService.save_file(file, upload_path)
                    PersonaCardFile.objects.create(
                        persona_card=persona_card,
                        **file_info
                    )
                    logger.info(
                        f"用户 {request.user.id} 创建人设卡 {persona_card.id} "
                        f"时上传文件: {file_info['original_name']}"
                    )
                
                # 增加上传限额计数
                UploadQuotaService.increment_quota(request.user.id)
                
                # 如果用户选择公开，触发审核流程
                want_public = str(request.data.get('is_public', '')).lower() == 'true'
                if want_public:
                    try:
                        PersonaCardService.submit_for_review(
                            persona_card, request.user
                        )
                        logger.info(
                            f"人设卡 {persona_card.id} 创建时选择公开，已提交审核"
                        )
                    except Exception as e:
                        logger.warning(
                            f"人设卡 {persona_card.id} 创建时自动提交审核失败: {e}"
                        )
            
            logger.info(
                f"用户 {request.user.id} 创建人设卡成功: {persona_card.id}, "
                f"剩余上传次数: {remaining - 1}"
            )
            
            # 返回创建的人设卡数据
            response_serializer = PersonaCardSerializer(
                persona_card,
                context={'request': request}
            )
            return DetailResponse(
                data=response_serializer.data,
                msg='创建成功'
            )
            
        except Exception as e:
            logger.error(
                f"创建人设卡失败: user_id={request.user.id}, error={str(e)}",
                exc_info=True
            )
            return ErrorResponse(msg=f'创建失败: {str(e)}', code=500)
    
    @swagger_auto_schema(
        operation_summary='确认敏感信息',
        operation_description='''
        确认配置中的敏感信息（5-11 位连续数字）不涉及个人隐私。
        
        流程：
        1. 验证确认声明格式
        2. 验证图片验证码
        3. 检查重试限制（最多 10 次）
        4. 记录确认信息到数据库（包含 IP 地址）
        
        重试限制：验证码错误 10 次后进入 1 分钟冷却期。
        ''',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['confirmation_text', 'sensitive_locations', 'captcha_key', 'captcha_value'],
            properties={
                'confirmation_text': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='确认声明（必须包含"确认"和"隐私"关键词）'
                ),
                'sensitive_locations': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description='敏感信息位置列表',
                    items=openapi.Schema(type=openapi.TYPE_STRING)
                ),
                'captcha_key': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='验证码 key'
                ),
                'captcha_value': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='验证码答案'
                )
            }
        ),
        responses={
            200: openapi.Response(
                description='确认成功',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='状态码'),
                        'msg': openapi.Schema(type=openapi.TYPE_STRING, description='消息'),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_STRING, description='确认记录 ID'),
                                'confirmation_text': openapi.Schema(type=openapi.TYPE_STRING, description='确认声明'),
                                'ip_address': openapi.Schema(type=openapi.TYPE_STRING, description='IP 地址'),
                                'confirmed_at': openapi.Schema(type=openapi.TYPE_STRING, description='确认时间')
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(description='验证码错误或确认声明格式不正确'),
            403: openapi.Response(description='只有创建者可以确认敏感信息'),
            429: openapi.Response(description='验证码错误次数过多，进入冷却期'),
            500: openapi.Response(description='确认失败')
        },
        tags=['人设卡上传']
    )
    @action(methods=['POST'], detail=True, url_path='confirm-sensitive')
    def confirm_sensitive(self, request, pk=None):
        """确认敏感信息（任务 14.3）
        
        验证确认声明格式，验证验证码，处理重试限制和冷却期，
        记录确认信息到数据库。
        
        需求：9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8
        
        Args:
            request: HTTP 请求对象
            pk: 人设卡 ID
            
        Returns:
            Response: 确认成功响应
        """
        from mainotebook.content.models import SensitiveInfoConfirmation
        
        persona_card = self.get_object()
        
        # 检查权限（只有创建者可以确认）
        if persona_card.uploader != request.user:
            return ErrorResponse(msg='只有创建者可以确认敏感信息', code=403)
        
        # 检查冷却期
        in_cooldown, remaining_time = CaptchaService.check_cooldown(request.user.id)
        if in_cooldown:
            logger.warning(
                f"用户在冷却期内尝试确认敏感信息: user_id={request.user.id}, "
                f"remaining={remaining_time}秒"
            )
            return ErrorResponse(
                msg=f'验证码错误次数过多，请 {remaining_time} 秒后再试',
                code=429
            )
        
        # 获取请求数据
        confirmation_text = request.data.get('confirmation_text', '')
        sensitive_locations = request.data.get('sensitive_locations', [])
        captcha_key = request.data.get('captcha_key', '')
        captcha_value = request.data.get('captcha_value', '')
        
        # 验证必需字段
        if not confirmation_text:
            return ErrorResponse(msg='请输入确认声明', code=400)
        
        if not sensitive_locations:
            return ErrorResponse(msg='敏感信息位置列表不能为空', code=400)
        
        if not captcha_key or not captcha_value:
            return ErrorResponse(msg='请输入验证码', code=400)
        
        # 验证确认声明格式（应包含所有配置项路径）
        # 简单验证：检查确认声明是否包含关键词
        if '确认' not in confirmation_text or '隐私' not in confirmation_text:
            logger.warning(
                f"确认声明格式不正确: user_id={request.user.id}, "
                f"text={confirmation_text}"
            )
            return ErrorResponse(
                msg='确认声明格式不正确，请使用提供的模板',
                code=400
            )
        
        # 验证验证码
        is_valid = CaptchaService.verify_captcha(captcha_key, captcha_value)
        
        if not is_valid:
            # 增加重试次数
            retry_count = CaptchaService.increment_retry_count(request.user.id)
            
            logger.warning(
                f"验证码验证失败: user_id={request.user.id}, "
                f"retry_count={retry_count}"
            )
            
            # 检查是否达到重试限制
            if retry_count >= CaptchaService.MAX_RETRY_COUNT:
                return ErrorResponse(
                    msg=f'验证码错误次数过多，请 {CaptchaService.COOLDOWN_SECONDS} 秒后再试',
                    code=429
                )
            
            remaining_attempts = CaptchaService.MAX_RETRY_COUNT - retry_count
            return ErrorResponse(
                msg=f'验证码错误，还可以尝试 {remaining_attempts} 次',
                code=400
            )
        
        # 验证码正确，重置重试次数
        CaptchaService.reset_retry_count(request.user.id)
        
        try:
            # 记录确认信息到数据库
            confirmation = SensitiveInfoConfirmation.objects.create(
                persona_card=persona_card,
                user=request.user,
                confirmation_text=confirmation_text,
                sensitive_locations=sensitive_locations,
                ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
                creator=request.user,
                modifier=request.user.username
            )
            
            logger.info(
                f"用户 {request.user.id} 确认人设卡 {persona_card.id} 的敏感信息成功, "
                f"IP: {confirmation.ip_address}"
            )
            
            from mainotebook.content.serializers.persona_card import SensitiveInfoConfirmationSerializer
            serializer = SensitiveInfoConfirmationSerializer(confirmation)
            
            return DetailResponse(
                data=serializer.data,
                msg='确认成功'
            )
            
        except Exception as e:
            logger.error(
                f"记录敏感信息确认失败: user_id={request.user.id}, "
                f"persona_card_id={persona_card.id}, error={str(e)}",
                exc_info=True
            )
            return ErrorResponse(msg=f'确认失败: {str(e)}', code=500)
    
    @swagger_auto_schema(
        method='get',
        operation_summary='获取人设卡配置项',
        operation_description='''
        获取人设卡的所有配置项，按配置块分组返回数据。
        只有上传者可以查看配置项。
        ''',
        responses={
            200: openapi.Response(
                description='获取成功',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='状态码'),
                        'msg': openapi.Schema(type=openapi.TYPE_STRING, description='消息'),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'sections': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    description='配置块列表',
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'name': openapi.Schema(type=openapi.TYPE_STRING, description='配置块名称'),
                                            'comment': openapi.Schema(type=openapi.TYPE_STRING, description='配置块注释'),
                                            'items': openapi.Schema(
                                                type=openapi.TYPE_ARRAY,
                                                description='配置项列表',
                                                items=openapi.Schema(
                                                    type=openapi.TYPE_OBJECT,
                                                    properties={
                                                        'key': openapi.Schema(type=openapi.TYPE_STRING, description='配置键名'),
                                                        'value': openapi.Schema(type=openapi.TYPE_STRING, description='配置值'),
                                                        'type': openapi.Schema(type=openapi.TYPE_STRING, description='数据类型'),
                                                        'comment': openapi.Schema(type=openapi.TYPE_STRING, description='配置项注释')
                                                    }
                                                )
                                            )
                                        }
                                    )
                                )
                            }
                        )
                    }
                )
            ),
            401: openapi.Response(description='请先登录'),
            403: openapi.Response(description='只有上传者可以查看配置项'),
            500: openapi.Response(description='获取失败')
        },
        tags=['人设卡配置管理']
    )
    @swagger_auto_schema(
        method='put',
        operation_summary='更新人设卡配置项',
        operation_description='''
        更新人设卡的配置项，支持批量更新和配置块删除标记。
        
        权限限制：
        - 只有上传者可以编辑
        - 审核中的人设卡不能编辑
        - 已通过审核的公开人设卡不能编辑
        ''',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'updates': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description='要更新的配置项列表',
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'section': openapi.Schema(type=openapi.TYPE_STRING, description='配置块名称'),
                            'key': openapi.Schema(type=openapi.TYPE_STRING, description='配置键名'),
                            'value': openapi.Schema(type=openapi.TYPE_STRING, description='新的配置值'),
                            'comment': openapi.Schema(type=openapi.TYPE_STRING, description='新的注释')
                        }
                    )
                ),
                'deleted_sections': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description='要标记为已删除的配置块名称列表',
                    items=openapi.Schema(type=openapi.TYPE_STRING)
                )
            }
        ),
        responses={
            200: openapi.Response(
                description='更新成功',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='状态码'),
                        'msg': openapi.Schema(type=openapi.TYPE_STRING, description='消息'),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description='更新后的配置项'
                        )
                    }
                )
            ),
            400: openapi.Response(description='请提供更新数据或配置项不存在'),
            401: openapi.Response(description='请先登录'),
            403: openapi.Response(description='无权限编辑此人设卡'),
            500: openapi.Response(description='更新失败')
        },
        tags=['人设卡配置管理']
    )
    @action(methods=['GET', 'PUT'], detail=True, url_path='config')
    def config(self, request, pk=None):
        """配置项管理（任务 15.1, 15.2）
        
        GET: 获取人设卡的所有配置项，按配置块分组返回数据
        PUT: 更新人设卡的配置项，支持批量更新和配置块删除标记
        
        需求：7.1, 7.2, 7.3, 7.4, 7.5, 12.3, 12.4
        
        Args:
            request: HTTP 请求对象
            pk: 人设卡 ID
            
        Returns:
            Response: 包含配置项的响应或更新成功响应
        """
        # 检查用户认证
        if not request.user.is_authenticated:
            return ErrorResponse(msg='请先登录', code=401)
        
        persona_card = self.get_object()
        
        if request.method == 'GET':
            # 获取配置项
            # 检查权限（只有上传者可以查看）
            if persona_card.uploader != request.user:
                logger.warning(
                    f"用户 {request.user.id} 尝试查看非自己的人设卡配置: "
                    f"persona_card_id={persona_card.id}"
                )
                return ErrorResponse(msg='只有上传者可以查看配置项', code=403)
            
            try:
                # 获取配置项
                configs = PersonaCardConfigService.get_configs(
                    persona_card,
                    include_deleted=False
                )
                
                # 按配置块分组返回数据，启用翻译
                formatted_data = PersonaCardConfigService.format_configs_as_dict(
                    configs,
                    translate=True,
                    translation_type='toml_visualizer_blocks'
                )
                
                # 检测敏感信息
                from mainotebook.content.services.sensitive_info_detector_service import SensitiveInfoDetectorService
                sections = formatted_data.get('sections', [])
                sensitive_items = SensitiveInfoDetectorService.detect_from_sections(sections)
                
                # 将敏感信息添加到返回数据中
                formatted_data['sensitive_info'] = sensitive_items
                
                logger.info(
                    f"用户 {request.user.id} 获取人设卡 {persona_card.id} 的配置项成功, "
                    f"检测到 {len(sensitive_items)} 处敏感信息"
                )
                
                return DetailResponse(
                    data=formatted_data,
                    msg='获取成功'
                )
                
            except Exception as e:
                logger.error(
                    f"获取配置项失败: persona_card_id={persona_card.id}, error={str(e)}",
                    exc_info=True
                )
                return ErrorResponse(msg=f'获取失败: {str(e)}', code=500)
        
        elif request.method == 'PUT':
            # 更新配置项
            from django.db import transaction
            
            # 检查编辑权限
            if not PersonaCardService.check_edit_permission(request.user, persona_card):
                logger.warning(
                    f"用户 {request.user.id} 尝试编辑无权限的人设卡: "
                    f"persona_card_id={persona_card.id}, "
                    f"is_pending={persona_card.is_pending}, "
                    f"is_public={persona_card.is_public}"
                )
                
                # 根据具体情况返回不同的错误消息
                if persona_card.uploader != request.user:
                    return ErrorResponse(msg='只有上传者可以编辑配置项', code=403)
                elif persona_card.is_pending:
                    return ErrorResponse(msg='审核中的人设卡不能编辑', code=403)
                elif persona_card.is_public:
                    return ErrorResponse(msg='已通过审核的公开人设卡不能编辑', code=403)
                else:
                    return ErrorResponse(msg='无权限编辑此人设卡', code=403)
            
            # 获取请求数据
            updates = request.data.get('updates', [])
            deleted_sections = request.data.get('deleted_sections', [])
            
            if not updates and not deleted_sections:
                return ErrorResponse(msg='请提供更新数据', code=400)
            
            try:
                # 使用事务更新配置项
                with transaction.atomic():
                    # 处理配置块删除标记
                    if deleted_sections:
                        for section_name in deleted_sections:
                            PersonaCardConfigService.delete_section(
                                persona_card,
                                section_name,
                                request.user
                            )
                            logger.info(
                                f"用户 {request.user.id} 标记人设卡 {persona_card.id} "
                                f"的配置块为已删除: {section_name}"
                            )
                    
                    # 更新配置项
                    if updates:
                        logger.info(
                            f"准备更新配置项: persona_card_id={persona_card.id}, "
                            f"updates={updates}"
                        )
                        updated_configs = PersonaCardConfigService.update_configs(
                            persona_card,
                            updates,
                            request.user
                        )
                        logger.info(
                            f"用户 {request.user.id} 更新人设卡 {persona_card.id} "
                            f"的配置项成功，共 {len(updated_configs)} 项"
                        )
                
                # 返回更新后的配置项
                configs = PersonaCardConfigService.get_configs(
                    persona_card,
                    include_deleted=False
                )
                formatted_data = PersonaCardConfigService.format_configs_as_dict(configs)
                
                return DetailResponse(
                    data=formatted_data,
                    msg='更新成功'
                )
                
            except ValueError as e:
                # 配置项不存在等验证错误
                logger.warning(
                    f"更新配置项验证失败: persona_card_id={persona_card.id}, "
                    f"error={str(e)}"
                )
                return ErrorResponse(msg=str(e), code=400)
            except Exception as e:
                logger.error(
                    f"更新配置项失败: persona_card_id={persona_card.id}, error={str(e)}",
                    exc_info=True
                )
                return ErrorResponse(msg=f'更新失败: {str(e)}', code=500)
    
    @swagger_auto_schema(
        operation_summary='导出 TOML 文件',
        operation_description='''
        导出人设卡的配置项为 TOML 格式。
        
        功能：
        - 将配置项格式化为有效的 TOML 文件
        - 保留配置项注释
        - 为被删除的配置块创建空块并添加注释
        - 返回 TOML 内容和被删除块列表
        
        权限：只有上传者可以导出配置。
        ''',
        responses={
            200: openapi.Response(
                description='导出成功',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='状态码'),
                        'msg': openapi.Schema(type=openapi.TYPE_STRING, description='消息'),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'content': openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    description='TOML 文件内容'
                                ),
                                'deleted_sections': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    description='被删除的配置块名称列表',
                                    items=openapi.Schema(type=openapi.TYPE_STRING)
                                )
                            }
                        )
                    }
                )
            ),
            403: openapi.Response(description='只有上传者可以导出配置'),
            500: openapi.Response(description='导出失败')
        },
        tags=['人设卡配置管理']
    )
    @action(methods=['POST'], detail=True, url_path='export-toml')
    def export_toml(self, request, pk=None):
        """导出 TOML 文件（任务 15.3）
        
        导出人设卡的配置项为 TOML 格式，返回 TOML 内容和被删除的块列表。
        只有上传者可以导出配置。
        
        需求：5.3, 5.4, 5.5, 5.6
        
        Args:
            request: HTTP 请求对象
            pk: 人设卡 ID
            
        Returns:
            Response: 包含 TOML 内容和被删除块列表的响应
        """
        from mainotebook.content.services.toml_exporter_service import TomlExporterService
        
        persona_card = self.get_object()
        
        # 检查权限（只有上传者可以导出）
        if persona_card.uploader != request.user:
            logger.warning(
                f"用户 {request.user.id} 尝试导出非自己的人设卡配置: "
                f"persona_card_id={persona_card.id}"
            )
            return ErrorResponse(msg='只有上传者可以导出配置', code=403)
        
        try:
            # 获取配置项（包含已删除的）
            configs = PersonaCardConfigService.get_configs(
                persona_card,
                include_deleted=True
            )
            
            # 导出 TOML
            toml_content = TomlExporterService.export_to_toml(
                configs,
                include_deleted=True
            )
            
            # 获取被删除的块列表
            deleted_sections = TomlExporterService.get_deleted_sections(configs)
            
            logger.info(
                f"用户 {request.user.id} 导出人设卡 {persona_card.id} 的 TOML 配置成功, "
                f"被删除块数量: {len(deleted_sections)}"
            )
            
            return DetailResponse(
                data={
                    'content': toml_content,
                    'deleted_sections': deleted_sections
                },
                msg='导出成功'
            )
            
        except Exception as e:
            logger.error(
                f"导出 TOML 失败: persona_card_id={persona_card.id}, error={str(e)}",
                exc_info=True
            )
            return ErrorResponse(msg=f'导出失败: {str(e)}', code=500)
    
    @swagger_auto_schema(
        operation_summary='下载人设卡',
        operation_description='''
        下载人设卡的 bot_config.toml 配置文件。
        
        功能：
        - 导出配置项为 TOML 格式
        - 增加下载计数
        - 记录下载历史（用户 ID、人设卡 ID、下载时间）
        - 返回文件响应（Content-Type: application/toml）
        
        权限：只有公开且已通过审核的人设卡可以下载。
        ''',
        responses={
            200: openapi.Response(
                description='下载成功，返回 TOML 文件',
                schema=openapi.Schema(
                    type=openapi.TYPE_FILE,
                    format='binary'
                ),
                headers={
                    'Content-Disposition': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description='attachment; filename="bot_config.toml"'
                    )
                }
            ),
            401: openapi.Response(description='请先登录'),
            403: openapi.Response(description='该人设卡未公开或正在审核中，无法下载'),
            500: openapi.Response(description='下载失败')
        },
        tags=['人设卡下载']
    )
    @action(methods=['GET'], detail=True, url_path='download')
    def download(self, request, pk=None):
        """下载人设卡（任务 15.4）
        
        下载人设卡的 TOML 配置文件，增加下载计数并记录下载历史。
        只有公开且已通过审核的人设卡可以下载。
        
        需求：13.1, 13.2, 13.3, 13.4, 13.8
        
        Args:
            request: HTTP 请求对象
            pk: 人设卡 ID
            
        Returns:
            FileResponse: TOML 文件响应
        """
        from django.http import HttpResponse
        from mainotebook.content.services.toml_exporter_service import TomlExporterService
        
        # 检查用户认证
        if not request.user.is_authenticated:
            return ErrorResponse(msg='请先登录', code=401)
        
        persona_card = self.get_object()
        
        # 检查下载权限
        if not PersonaCardService.check_download_permission(request.user, persona_card):
            logger.warning(
                f"用户 {request.user.id} 尝试下载无权限的人设卡: "
                f"persona_card_id={persona_card.id}, "
                f"is_public={persona_card.is_public}, is_pending={persona_card.is_pending}"
            )
            
            # 根据具体情况返回不同的错误消息
            if not persona_card.is_public:
                return ErrorResponse(msg='该人设卡未公开，无法下载', code=403)
            elif persona_card.is_pending:
                return ErrorResponse(msg='该人设卡正在审核中，暂时无法下载', code=403)
            else:
                return ErrorResponse(msg='无权限下载此人设卡', code=403)
        
        try:
            # 获取配置项（不包含已删除的）
            configs = PersonaCardConfigService.get_configs(
                persona_card,
                include_deleted=False
            )
            
            # 导出 TOML
            toml_content = TomlExporterService.export_to_toml(
                configs,
                include_deleted=False
            )
            
            # 增加下载计数
            persona_card.downloads += 1
            persona_card.save(update_fields=['downloads'])
            
            # 记录下载历史（如果模型存在）
            try:
                from mainotebook.content.models import PersonaCardDownloadHistory
                PersonaCardDownloadHistory.objects.create(
                    persona_card=persona_card,
                    user=request.user,
                    creator=request.user,
                    modifier=request.user.username
                )
            except ImportError:
                # 如果模型不存在，跳过记录下载历史
                pass
            
            logger.info(
                f"用户 {request.user.id} 下载人设卡 {persona_card.id} 成功, "
                f"当前下载次数: {persona_card.downloads}"
            )
            
            # 返回文件响应
            response = HttpResponse(
                toml_content,
                content_type='application/toml'
            )
            response['Content-Disposition'] = 'attachment; filename="bot_config.toml"'
            
            return response
            
        except Exception as e:
            logger.error(
                f"下载人设卡失败: persona_card_id={persona_card.id}, error={str(e)}",
                exc_info=True
            )
            return ErrorResponse(msg=f'下载失败: {str(e)}', code=500)

    @swagger_auto_schema(
        operation_summary='切换人设卡公开/私有状态',
        operation_description='''
        切换人设卡的公开/私有状态。
        
        状态转换：
        - 公开转私有：设置 is_public=False，保持 is_pending=False
        - 私有转公开：设置 is_public=True，is_pending=True，触发 AI 自动审核
        
        权限：只有上传者可以切换状态。
        ''',
        responses={
            200: openapi.Response(
                description='操作成功',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='状态码'),
                        'msg': openapi.Schema(type=openapi.TYPE_STRING, description='消息'),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_STRING, description='人设卡 ID'),
                                'is_public': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='是否公开'),
                                'is_pending': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='是否待审核')
                            }
                        )
                    }
                )
            ),
            403: openapi.Response(description='只有上传者可以切换人设卡状态'),
            404: openapi.Response(description='人设卡不存在'),
            500: openapi.Response(description='操作失败')
        },
        tags=['人设卡状态管理']
    )
    @action(methods=['post'], detail=True, url_path='toggle-public')
    def toggle_public(self, request, pk=None):
        """切换人设卡公开/私有状态（任务 16.1）
        
        实现公开转私有和私有转公开的状态切换：
        - 公开转私有：设置 is_public=False，保持 is_pending=False
        - 私有转公开：设置 is_public=True，is_pending=True，触发审核
        
        需求：12.5, 12.6, 12.7
        
        Args:
            request: HTTP 请求对象
            pk: 人设卡 ID
            
        Returns:
            Response: 操作结果响应
        """
        # 直接获取对象，不使用 get_queryset 过滤
        try:
            persona_card = PersonaCard.objects.get(pk=pk)
        except PersonaCard.DoesNotExist:
            return ErrorResponse(msg='人设卡不存在', code=404)
        
        # 检查用户权限（只有上传者可以操作）
        if persona_card.uploader != request.user:
            logger.warning(
                f"用户 {request.user.id} 尝试切换非自己的人设卡状态: "
                f"persona_card_id={persona_card.id}, uploader_id={persona_card.uploader_id}"
            )
            return ErrorResponse(msg='只有上传者可以切换人设卡状态', code=403, status=403)
        
        try:
            # 记录原始状态
            original_is_public = persona_card.is_public
            
            if persona_card.is_public:
                # 公开转私有
                persona_card.is_public = False
                # 保持 is_pending=False（需求 12.6）
                persona_card.is_pending = False
                persona_card.save(update_fields=['is_public', 'is_pending'])
                
                logger.info(
                    f"人设卡 {persona_card.id} 从公开转为私有, "
                    f"user_id={request.user.id}"
                )
                
                return DetailResponse(
                    data={
                        'id': str(persona_card.id),
                        'is_public': persona_card.is_public,
                        'is_pending': persona_card.is_pending
                    },
                    msg='已将人设卡设为私有'
                )
            else:
                # 私有转公开：触发审核流程（需求 12.7）
                try:
                    # 设置为公开且待审核状态
                    persona_card.is_public = True
                    persona_card.is_pending = True
                    persona_card.save(update_fields=['is_public', 'is_pending'])
                    
                    # 触发 AI 自动审核异步任务
                    try:
                        from mainotebook.content.tasks import auto_review_task
                        auto_review_task.delay(str(persona_card.id), 'persona')
                    except Exception as task_error:
                        logger.warning(
                            f"触发 AI 自动审核任务失败: persona_card_id={persona_card.id}, "
                            f"error={str(task_error)}"
                        )
                    
                    logger.info(
                        f"人设卡 {persona_card.id} 从私有转为公开，已触发审核, "
                        f"user_id={request.user.id}"
                    )
                    
                    return DetailResponse(
                        data={
                            'id': str(persona_card.id),
                            'is_public': persona_card.is_public,
                            'is_pending': persona_card.is_pending
                        },
                        msg='已将人设卡设为公开，正在审核中'
                    )
                except Exception as e:
                    # 如果设置失败，回滚状态
                    persona_card.is_public = original_is_public
                    persona_card.is_pending = False
                    persona_card.save(update_fields=['is_public', 'is_pending'])
                    
                    logger.error(
                        f"设置公开失败: persona_card_id={persona_card.id}, error={str(e)}",
                        exc_info=True
                    )
                    return ErrorResponse(msg=f'设置公开失败: {str(e)}', code=500)
                    
        except Exception as e:
            logger.error(
                f"切换人设卡状态失败: persona_card_id={persona_card.id}, error={str(e)}",
                exc_info=True
            )
            return ErrorResponse(msg=f'操作失败: {str(e)}', code=500)

    @swagger_auto_schema(
        operation_summary='更新人设卡基本信息',
        operation_description='更新人设卡的基本信息（名称、描述、版权所有者、标签）',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='人设卡名称（1-200字符）'),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='人设卡描述（至少10字符）'),
                'copyright_owner': openapi.Schema(type=openapi.TYPE_STRING, description='版权所有者'),
                'tags': openapi.Schema(type=openapi.TYPE_STRING, description='标签（逗号分隔）')
            }
        ),
        responses={
            200: openapi.Response(description='更新成功'),
            400: openapi.Response(description='参数错误'),
            401: openapi.Response(description='请先登录'),
            403: openapi.Response(description='无权限编辑此人设卡'),
            404: openapi.Response(description='人设卡不存在'),
            500: openapi.Response(description='更新失败')
        },
        tags=['人设卡管理']
    )
    @action(methods=['PUT'], detail=True, url_path='basic-info')
    def update_basic_info(self, request, pk=None):
        """更新人设卡基本信息
        
        允许用户更新人设卡的基本信息（名称、描述、版权所有者、标签）
        只有私有状态且未在审核中的人设卡可以编辑
        
        Args:
            request: HTTP 请求对象
            pk: 人设卡 ID
            
        Returns:
            Response: 更新结果响应
        """
        # 检查用户认证
        if not request.user.is_authenticated:
            return ErrorResponse(msg='请先登录', code=401)
        
        # 获取人设卡对象
        try:
            persona_card = PersonaCard.objects.get(pk=pk)
        except PersonaCard.DoesNotExist:
            return ErrorResponse(msg='人设卡不存在', code=404)
        
        # 检查编辑权限
        if not PersonaCardService.check_edit_permission(request.user, persona_card):
            logger.warning(
                f"用户 {request.user.id} 尝试编辑无权限的人设卡: "
                f"persona_card_id={persona_card.id}, "
                f"is_pending={persona_card.is_pending}, "
                f"is_public={persona_card.is_public}"
            )
            
            # 根据具体情况返回不同的错误消息
            if persona_card.uploader != request.user:
                return ErrorResponse(msg='只有上传者可以编辑基本信息', code=403)
            elif persona_card.is_pending:
                return ErrorResponse(msg='审核中的人设卡不能编辑', code=403)
            elif persona_card.is_public:
                return ErrorResponse(msg='已通过审核的公开人设卡不能编辑', code=403)
            else:
                return ErrorResponse(msg='无权限编辑此人设卡', code=403)
        
        # 获取更新数据
        name = request.data.get('name')
        description = request.data.get('description')
        copyright_owner = request.data.get('copyright_owner')
        tags = request.data.get('tags')
        
        # 验证必填字段
        if not name or not description:
            return ErrorResponse(msg='名称和描述不能为空', code=400)
        
        # 验证字段长度
        if len(name) < 1 or len(name) > 200:
            return ErrorResponse(msg='名称长度必须在1-200字符之间', code=400)
        
        if len(description) < 10:
            return ErrorResponse(msg='描述至少需要10个字符', code=400)
        
        try:
            # 准备更新数据
            update_data = {
                'name': name,
                'description': description,
            }
            
            # 可选字段
            if copyright_owner is not None:
                update_data['copyright_owner'] = copyright_owner
            
            if tags is not None:
                update_data['tags'] = tags
            
            # 调用 Service 层更新
            updated_card = PersonaCardService.update_persona_card(
                persona_card,
                request.user,
                update_data
            )
            
            logger.info(
                f"用户 {request.user.id} 更新人设卡 {persona_card.id} 的基本信息成功"
            )
            
            return DetailResponse(
                data={
                    'id': str(updated_card.id),
                    'name': updated_card.name,
                    'description': updated_card.description,
                    'copyright_owner': updated_card.copyright_owner,
                    'tags': updated_card.tags
                },
                msg='更新成功'
            )
            
        except Exception as e:
            logger.error(
                f"更新基本信息失败: persona_card_id={persona_card.id}, error={str(e)}",
                exc_info=True
            )
            return ErrorResponse(msg=f'更新失败: {str(e)}', code=500)

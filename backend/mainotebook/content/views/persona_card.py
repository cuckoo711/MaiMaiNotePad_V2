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
        """根据操作类型和用户角色返回不同的查询集
        
        权限规则：
        - 超级管理员/管理员/审核员：可查看所有内容
        - 普通用户：
          - list（广场）: 只能看公开且已审核的内容
          - my（内容管理）: 只能看自己创建的内容
          - retrieve/file_detail: 可查看公开内容和自己的内容
        
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
        
        # list 操作（广场）：只返回公开且已审核的人设卡
        if self.action == 'list':
            queryset = PersonaCard.objects.filter(
                is_public=True,
                is_pending=False
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
                # 管理员/审核员可查看所有
                if is_admin_or_reviewer:
                    return PersonaCard.objects.all()
                # 普通用户只能看公开内容和自己的
                return PersonaCard.objects.filter(
                    models.Q(is_public=True, is_pending=False) | models.Q(uploader=user)
                )
            # 未登录用户只能看公开内容
            return PersonaCard.objects.filter(is_public=True, is_pending=False)
        
        # 其他操作（create/update/delete/files 等）
        # 管理员/审核员可操作所有
        if is_admin_or_reviewer:
            return PersonaCard.objects.all()
        
        # 普通用户只能操作自己的
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

# -*- coding: utf-8 -*-

"""
知识库视图集

提供知识库的 CRUD 操作和文件管理功能。
"""

import os
import json
import logging
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
from mainotebook.content.services.tag_service import TagService

logger = logging.getLogger(__name__)
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
    # 数据权限过滤：普通用户只能看到自己的内容，管理员和审核员可以看到所有内容
    # extra_filter_class 留空，在 get_queryset 中根据用户角色动态过滤
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
        """根据操作类型和用户角色返回不同的查询集
        
        权限规则：
        - 超级管理员/管理员/审核员：可查看所有内容
        - 普通用户：
          - list（广场）: 只能看公开且已审核的内容
          - my（内容管理）: 只能看自己创建的内容
          - retrieve/file_detail: 可查看公开内容和自己的内容
        
        Returns:
            QuerySet: 知识库查询集
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
        
        # list 操作（广场）：只返回公开且已审核的知识库
        if self.action == 'list':
            queryset = KnowledgeBase.objects.filter(
                is_public=True,
                is_pending=False
            )
            
            # 处理收藏筛选
            starred_param = self.request.query_params.get('starred', '').lower()
            if starred_param == 'true' and user.is_authenticated:
                # 只返回当前用户收藏的知识库
                from mainotebook.content.models import StarRecord
                import uuid as uuid_module
                
                # 获取收藏的 target_id（字符串格式）
                starred_id_strs = StarRecord.objects.filter(
                    user=user,
                    target_type='knowledge'
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
        
        # my 操作（内容管理 - 我的知识库）：已在 my 方法中处理，这里不会被调用
        
        # retrieve/file_detail 操作：查看详情
        if self.action in ('retrieve', 'file_detail'):
            if user and user.is_authenticated:
                # 管理员/审核员可查看所有
                if is_admin_or_reviewer:
                    return KnowledgeBase.objects.all()
                # 普通用户只能看公开内容和自己的
                return KnowledgeBase.objects.filter(
                    models.Q(is_public=True, is_pending=False) | models.Q(uploader=user)
                )
            # 未登录用户只能看公开内容
            return KnowledgeBase.objects.filter(is_public=True, is_pending=False)
        
        # 其他操作（create/update/delete/files 等）
        # 管理员/审核员可操作所有
        if is_admin_or_reviewer:
            return KnowledgeBase.objects.all()
        
        # 普通用户只能操作自己的
        if user and user.is_authenticated:
            return KnowledgeBase.objects.filter(uploader=user)
        
        # 未登录用户返回空查询集
        return KnowledgeBase.objects.none()
    
    def list(self, request, *args, **kwargs):
        """获取知识库列表
        
        重写 list 方法以记录标签搜索统计。
        
        Args:
            request: HTTP 请求对象
            
        Returns:
            Response: 知识库列表响应
        """
        # 记录标签搜索统计
        tags_param = request.query_params.get('tags', '')
        if tags_param:
            # 解析标签参数（可能是逗号分隔的多个标签）
            tags = [tag.strip() for tag in tags_param.split(',') if tag.strip()]
            for tag in tags:
                try:
                    TagService.increment_search_count(tag, tag_type='knowledge')
                except Exception as e:
                    logger.warning(f"记录标签搜索统计失败: {tag}, {e}")
        
        # 调用父类的 list 方法
        return super().list(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        """创建知识库后处理上传的文件，用户选择公开时自动提交审核

        创建流程统一为：先创建私有知识库 → 处理文件 → 如果用户选择了公开则调用
        submit_for_review 走统一审核流程，确保审核入口唯一，避免重复通知。

        Args:
            serializer: 知识库创建序列化器
        """
        # 记录用户是否选择了公开（serializer 已将 is_public 统一设为 False）
        want_public = str(self.request.data.get('is_public', '')).lower() == 'true'

        knowledge_base = serializer.save()

        # 更新标签使用统计
        if knowledge_base.tags:
            tags = [tag.strip() for tag in knowledge_base.tags.split(',') if tag.strip()]
            try:
                TagService.update_tag_usage(tags, tag_type='knowledge')
            except Exception as e:
                logger.warning(f"更新标签使用统计失败: {e}")

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

        # 用户选择公开时，通过 submit_for_review 统一走审核流程
        if want_public:
            try:
                KnowledgeBaseService.submit_for_review(
                    knowledge_base, self.request.user
                )
                logger.info(f"知识库 {knowledge_base.id} 创建时选择公开，已提交审核")
            except Exception as e:
                logger.warning(
                    f"知识库 {knowledge_base.id} 创建时自动提交审核失败: {e}"
                )
    
    def perform_update(self, serializer):
        """更新知识库后更新标签使用统计
        
        Args:
            serializer: 知识库更新序列化器
        """
        # 获取旧的标签
        old_tags = set()
        if serializer.instance.tags:
            old_tags = set(tag.strip() for tag in serializer.instance.tags.split(',') if tag.strip())
        
        # 保存更新
        knowledge_base = serializer.save()
        
        # 获取新的标签
        new_tags = set()
        if knowledge_base.tags:
            new_tags = set(tag.strip() for tag in knowledge_base.tags.split(',') if tag.strip())
        
        # 计算新增的标签
        added_tags = new_tags - old_tags
        if added_tags:
            try:
                TagService.update_tag_usage(list(added_tags), tag_type='knowledge')
            except Exception as e:
                logger.warning(f"更新标签使用统计失败: {e}")
    
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
        url_path='files/(?P<file_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
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
            # 增加下载计数
            from django.db.models import F
            KnowledgeBase.objects.filter(id=knowledge_base.id).update(
                downloads=F('downloads') + 1
            )
            
            # 记录下载记录
            from mainotebook.content.models import DownloadRecord
            DownloadRecord.objects.create(
                target_id=str(knowledge_base.id),
                target_type='knowledge'
            )
            
            logger.info(f"用户 {request.user.id} 下载知识库 {knowledge_base.id} 的文件 {kb_file.original_name}")
            
            return FileService.get_file_response(kb_file.file_path, kb_file.original_name)
        except FileNotFoundError:
            return ErrorResponse(msg="文件不存在", status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return ErrorResponse(msg=f"文件下载失败: {str(e)}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(methods=['POST'], detail=True, url_path='parse_file')
    def parse_file(self, request, pk=None):
        """解析知识库文件并返回结构化数据
        
        支持的文件类型：
        - JSON: 解析并分页返回文档列表
        - TXT: 返回文本内容
        - 压缩包: 返回提示信息，建议下载
        
        Args:
            request: HTTP 请求对象
            pk: 知识库 ID
            
        Request Body:
            file_id: 文件 ID（必需）
            page: 页码（仅 JSON，默认 1）
            page_size: 每页数量（仅 JSON，默认 20）
            search: 搜索关键词（可选）
            
        Returns:
            Response: 包含解析结果的响应
        """
        # 从请求体获取参数
        file_id = request.data.get('file_id')
        if not file_id:
            return ErrorResponse(msg='缺少 file_id 参数', code=400)
        
        knowledge_base = self.get_object()
        
        try:
            kb_file = KnowledgeBaseFile.objects.get(
                id=file_id,
                knowledge_base=knowledge_base
            )
        except KnowledgeBaseFile.DoesNotExist:
            return ErrorResponse(msg='文件不存在', code=404)
        
        from django.conf import settings
        full_path = os.path.join(settings.MEDIA_ROOT, kb_file.file_path)
        file_name = kb_file.original_name.lower()
        
        try:
            # JSON 文件
            if file_name.endswith('.json'):
                return self._parse_json_file(full_path, request, kb_file)
            
            # TXT 文件
            elif file_name.endswith('.txt'):
                return self._parse_txt_file(full_path, request, kb_file)
            
            # 压缩包
            elif file_name.endswith(('.zip', '.rar', '.7z', '.tar', '.gz', '.tar.gz')):
                return DetailResponse(
                    data={
                        'file_type': 'archive',
                        'file_name': kb_file.original_name,
                        'file_size': kb_file.file_size,
                        'message': '压缩包文件暂不支持在线预览，请下载后查看'
                    },
                    msg='压缩包文件'
                )
            
            else:
                return ErrorResponse(msg='不支持的文件类型')
                
        except Exception as e:
            logger.error(f"解析文件失败: {kb_file.file_path}, 错误: {e}")
            return ErrorResponse(msg=f'解析失败: {str(e)}')
    
    def _parse_json_file(self, file_path: str, request, kb_file):
        """解析 JSON 文件（支持搜索和分页）
        
        Args:
            file_path: 文件路径
            request: HTTP 请求对象
            kb_file: 文件记录对象
            
        Returns:
            Response: 包含分页数据的响应
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 从请求体获取参数
            search_keyword = request.data.get('search', '').strip()
            page = int(request.data.get('page', 1))
            page_size = int(request.data.get('page_size', 20))
            
            # 提取文档列表
            docs = data.get('docs', [])
            
            # 计算统计信息（基于全部文档）
            total_docs = len(docs)
            if total_docs > 0:
                total_passage_len = sum(len(doc.get('passage', '')) for doc in docs)
                total_entities = sum(len(doc.get('extracted_entities', [])) for doc in docs)
                total_triples = sum(len(doc.get('extracted_triples', [])) for doc in docs)
                
                avg_passage_len = total_passage_len / total_docs
                avg_entities = total_entities / total_docs
                avg_triples = total_triples / total_docs
            else:
                total_passage_len = 0
                avg_passage_len = 0
                avg_entities = 0
                avg_triples = 0
                total_entities = 0
                total_triples = 0
            
            # 如果有搜索关键词，进行过滤
            if search_keyword:
                keyword_lower = search_keyword.lower()
                filtered_docs = []
                
                for doc in docs:
                    # 搜索段落内容
                    if doc.get('passage', '').lower().find(keyword_lower) != -1:
                        filtered_docs.append(doc)
                        continue
                    
                    # 搜索实体
                    entities = doc.get('extracted_entities', [])
                    if any(keyword_lower in str(e).lower() for e in entities):
                        filtered_docs.append(doc)
                        continue
                    
                    # 搜索三元组
                    triples = doc.get('extracted_triples', [])
                    if any(
                        any(keyword_lower in str(item).lower() for item in triple)
                        for triple in triples
                    ):
                        filtered_docs.append(doc)
                        continue
                
                docs = filtered_docs
            
            total = len(docs)
            
            # 计算分页
            start = (page - 1) * page_size
            end = start + page_size
            page_docs = docs[start:end]
            
            # 构建响应数据
            result = {
                'file_type': 'json',
                'file_name': kb_file.original_name,
                'total_docs': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size if total > 0 else 0,
                'docs': page_docs,
                'metadata': {
                    'total_chars': total_passage_len,
                    'avg_passage_len': round(avg_passage_len, 1),
                    'avg_entities': round(avg_entities, 1),
                    'avg_triples': round(avg_triples, 1),
                    'total_entities': total_entities,
                    'total_triples': total_triples
                },
                'search_keyword': search_keyword if search_keyword else None
            }
            
            logger.info(
                f"用户 {request.user.id if request.user.is_authenticated else '匿名'} "
                f"解析知识库 {kb_file.knowledge_base.id} 的 JSON 文件: {kb_file.original_name}, "
                f"第 {page} 页{f', 搜索: {search_keyword}' if search_keyword else ''}"
            )
            
            return DetailResponse(data=result, msg='解析成功')
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {file_path}, 错误: {e}")
            return ErrorResponse(msg=f'JSON 格式错误: {str(e)}')
    
    def _parse_txt_file(self, file_path: str, request, kb_file):
        """解析 TXT 文件（按段落分割，支持搜索）
        
        TXT 文件格式：每个段落之间用空行分隔，每个段落是一条知识条目
        
        Args:
            file_path: 文件路径
            request: HTTP 请求对象
            kb_file: 文件记录对象
            
        Returns:
            Response: 包含段落列表的响应
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 按空行分割段落
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            
            # 从请求体获取搜索关键词
            search_keyword = request.data.get('search', '').strip()
            
            # 如果有搜索关键词，进行过滤
            if search_keyword:
                keyword_lower = search_keyword.lower()
                paragraphs = [
                    p for p in paragraphs 
                    if keyword_lower in p.lower()
                ]
            
            result = {
                'file_type': 'txt',
                'file_name': kb_file.original_name,
                'total_paragraphs': len(paragraphs),
                'paragraphs': paragraphs,
                'search_keyword': search_keyword if search_keyword else None
            }
            
            logger.info(
                f"解析知识库 {kb_file.knowledge_base.id} 的 TXT 文件: {kb_file.original_name}, "
                f"共 {len(paragraphs)} 个段落{f', 搜索: {search_keyword}' if search_keyword else ''}"
            )
            
            return DetailResponse(data=result, msg='解析成功')
            
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
                
                # 按空行分割段落
                paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
                
                # 从请求体获取搜索关键词
                search_keyword = request.data.get('search', '').strip()
                
                # 如果有搜索关键词，进行过滤
                if search_keyword:
                    keyword_lower = search_keyword.lower()
                    paragraphs = [
                        p for p in paragraphs 
                        if keyword_lower in p.lower()
                    ]
                
                result = {
                    'file_type': 'txt',
                    'file_name': kb_file.original_name,
                    'total_paragraphs': len(paragraphs),
                    'paragraphs': paragraphs,
                    'encoding': 'gbk',
                    'search_keyword': search_keyword if search_keyword else None
                }
                
                return DetailResponse(data=result, msg='解析成功')
            except Exception as e:
                return ErrorResponse(msg=f'文件编码错误: {str(e)}')
    
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

"""
知识库服务

提供知识库相关的业务逻辑。
"""

from typing import Optional
from django.db.models import QuerySet, Q
from django.core.exceptions import ValidationError, PermissionDenied
from mainotebook.system.models import Users
from ..models import KnowledgeBase, StarRecord, UploadRecord


class KnowledgeBaseService:
    """知识库服务
    
    提供知识库相关的业务逻辑。
    """
    
    @staticmethod
    def get_public_knowledge_bases(
        filters: Optional[dict] = None,
        ordering: str = '-create_datetime'
    ) -> QuerySet:
        """获取公开知识库列表
        
        Args:
            filters: 过滤条件字典，支持 search（搜索关键词）、tags（标签）
            ordering: 排序字段，默认按创建时间倒序
            
        Returns:
            QuerySet: 知识库查询集
        """
        # 基础查询：公开、已审核、未删除
        queryset = KnowledgeBase.objects.filter(
            is_public=True,
            is_pending=False
        )
        
        # 如果模型有 is_deleted 字段，过滤已删除的记录
        if hasattr(KnowledgeBase, 'is_deleted'):
            queryset = queryset.filter(is_deleted=False)
        
        # 应用过滤条件
        if filters:
            # 搜索关键词（在名称、描述、标签中搜索）
            if 'search' in filters and filters['search']:
                search = filters['search']
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(description__icontains=search) |
                    Q(tags__icontains=search)
                )
            
            # 标签过滤
            if 'tags' in filters and filters['tags']:
                queryset = queryset.filter(tags__icontains=filters['tags'])
        
        # 应用排序
        return queryset.order_by(ordering)
    
    @staticmethod
    def get_user_knowledge_bases(user: Users) -> QuerySet:
        """获取用户的知识库列表
        
        Args:
            user: 用户对象
            
        Returns:
            QuerySet: 知识库查询集（不包含已删除的）
        """
        queryset = KnowledgeBase.objects.filter(uploader=user)
        
        # 如果模型有 is_deleted 字段，过滤已删除的记录
        if hasattr(KnowledgeBase, 'is_deleted'):
            queryset = queryset.filter(is_deleted=False)
        
        return queryset.order_by('-create_datetime')
    
    @staticmethod
    def create_knowledge_base(user: Users, data: dict) -> KnowledgeBase:
        """创建知识库
        
        Args:
            user: 创建者
            data: 知识库数据，包含 name、description 等字段
            
        Returns:
            KnowledgeBase: 创建的知识库对象
            
        Raises:
            ValidationError: 当数据验证失败时（如名称重复）
        """
        # 验证名称唯一性（在用户范围内）
        if KnowledgeBase.objects.filter(
            uploader=user,
            name=data['name']
        ).exists():
            raise ValidationError("您已经创建了同名的知识库")
        
        # 创建知识库
        knowledge_base = KnowledgeBase.objects.create(
            uploader=user,
            **data
        )
        
        # 创建上传记录
        UploadRecord.objects.create(
            uploader=user,
            target_id=str(knowledge_base.id),
            target_type='knowledge',
            name=knowledge_base.name,
            description=knowledge_base.description,
            status='pending'
        )
        
        return knowledge_base
    
    @staticmethod
    def update_knowledge_base(
        knowledge_base: KnowledgeBase,
        user: Users,
        data: dict
    ) -> KnowledgeBase:
        """更新知识库
        
        Args:
            knowledge_base: 知识库对象
            user: 当前用户
            data: 更新数据
            
        Returns:
            KnowledgeBase: 更新后的知识库对象
            
        Raises:
            PermissionDenied: 当用户无权限时
        """
        # 验证权限（仅创建者可修改）
        if knowledge_base.uploader != user:
            raise PermissionDenied("只有创建者可以修改知识库")
        
        # 更新字段
        for key, value in data.items():
            setattr(knowledge_base, key, value)
        
        knowledge_base.save()
        return knowledge_base
    
    @staticmethod
    def delete_knowledge_base(knowledge_base: KnowledgeBase, user: Users) -> None:
        """删除知识库（软删除）
        
        Args:
            knowledge_base: 知识库对象
            user: 当前用户
            
        Raises:
            PermissionDenied: 当用户无权限时
        """
        # 验证权限（仅创建者可删除）
        if knowledge_base.uploader != user:
            raise PermissionDenied("只有创建者可以删除知识库")
        
        # 软删除
        knowledge_base.is_deleted = True
        knowledge_base.save()
        
        # 删除关联的收藏记录
        StarRecord.objects.filter(
            target_id=str(knowledge_base.id),
            target_type='knowledge'
        ).delete()
    
    @staticmethod
    def submit_for_review(knowledge_base: KnowledgeBase, user: Users) -> None:
        """提交知识库审核
        
        Args:
            knowledge_base: 知识库对象
            user: 当前用户
            
        Raises:
            PermissionDenied: 当用户无权限时
            ValidationError: 当状态不允许提交时
        """
        # 验证权限（仅创建者可提交审核）
        if knowledge_base.uploader != user:
            raise PermissionDenied("只有创建者可以提交审核")
        
        # 验证状态（不能重复提交）
        if knowledge_base.is_pending:
            raise ValidationError("知识库已处于待审核状态")
        
        # 更新状态
        knowledge_base.is_pending = True
        knowledge_base.is_public = False
        knowledge_base.save()
        
        # 更新上传记录
        UploadRecord.objects.filter(
            target_id=str(knowledge_base.id),
            target_type='knowledge'
        ).update(status='pending')

        # 触发 AI 自动审核异步任务
        try:
            from mainotebook.content.tasks import auto_review_task
            auto_review_task.delay(str(knowledge_base.id), 'knowledge')
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                "触发 AI 自动审核任务失败: knowledge_base_id=%s", knowledge_base.id
            )

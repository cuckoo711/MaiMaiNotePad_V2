"""
人设卡服务

提供人设卡相关的业务逻辑。
"""

from typing import Optional, Tuple
from django.db.models import QuerySet, Q
from django.core.exceptions import ValidationError, PermissionDenied
from mainotebook.system.models import Users
from ..models import PersonaCard, PersonaCardFile, StarRecord, UploadRecord
from .toml_validator import TOMLValidator


class PersonaCardService:
    """人设卡服务
    
    提供人设卡相关的业务逻辑。
    """
    
    @staticmethod
    def get_public_persona_cards(
        filters: Optional[dict] = None,
        ordering: str = '-create_datetime'
    ) -> QuerySet:
        """获取公开人设卡列表
        
        Args:
            filters: 过滤条件字典，支持 search（搜索关键词）、tags（标签）
            ordering: 排序字段，默认按创建时间倒序
            
        Returns:
            QuerySet: 人设卡查询集
        """
        # 基础查询：公开、已审核
        queryset = PersonaCard.objects.filter(
            is_public=True,
            is_pending=False
        )
        
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
    def get_user_persona_cards(user: Users) -> QuerySet:
        """获取用户的人设卡列表
        
        Args:
            user: 用户对象
            
        Returns:
            QuerySet: 人设卡查询集
        """
        return PersonaCard.objects.filter(
            uploader=user
        ).order_by('-create_datetime')
    
    @staticmethod
    def validate_toml_file(persona_card: PersonaCard) -> Tuple[bool, str]:
        """验证人设卡的 TOML 文件
        
        Args:
            persona_card: 人设卡对象
            
        Returns:
            tuple[bool, str]: (是否有效, 错误信息)
        """
        # 检查是否包含且仅包含一个 bot_config.toml 文件
        toml_files = persona_card.files.filter(original_name='bot_config.toml')
        
        if toml_files.count() == 0:
            return False, "人设卡必须包含 bot_config.toml 文件"
        
        if toml_files.count() > 1:
            return False, "人设卡只能包含一个 bot_config.toml 文件"
        
        # 验证 TOML 文件内容
        toml_file = toml_files.first()
        try:
            is_valid, error_msg = TOMLValidator.validate_file(toml_file.file_path)
            return is_valid, error_msg
        except Exception as e:
            return False, f"TOML 文件验证失败: {str(e)}"
    
    @staticmethod
    def create_persona_card(user: Users, data: dict) -> PersonaCard:
        """创建人设卡
        
        Args:
            user: 创建者
            data: 人设卡数据，包含 name、description 等字段
            
        Returns:
            PersonaCard: 创建的人设卡对象
            
        Raises:
            ValidationError: 当数据验证失败时（如名称重复）
        """
        # 验证名称唯一性（在用户范围内）
        if PersonaCard.objects.filter(
            uploader=user,
            name=data['name']
        ).exists():
            raise ValidationError("您已经创建了同名的人设卡")
        
        # 创建人设卡
        persona_card = PersonaCard.objects.create(
            uploader=user,
            **data
        )
        
        # 创建上传记录
        UploadRecord.objects.create(
            uploader=user,
            target_id=str(persona_card.id),
            target_type='persona',
            name=persona_card.name,
            description=persona_card.description,
            status='pending'
        )
        
        return persona_card
    
    @staticmethod
    def update_persona_card(
        persona_card: PersonaCard,
        user: Users,
        data: dict
    ) -> PersonaCard:
        """更新人设卡
        
        Args:
            persona_card: 人设卡对象
            user: 当前用户
            data: 更新数据
            
        Returns:
            PersonaCard: 更新后的人设卡对象
            
        Raises:
            PermissionDenied: 当用户无权限时
        """
        # 验证权限（仅创建者可修改）
        if persona_card.uploader != user:
            raise PermissionDenied("只有创建者可以修改人设卡")
        
        # 更新字段
        for key, value in data.items():
            setattr(persona_card, key, value)
        
        persona_card.save()
        return persona_card
    
    @staticmethod
    def delete_persona_card(persona_card: PersonaCard, user: Users) -> None:
        """删除人设卡（硬删除）
        
        Args:
            persona_card: 人设卡对象
            user: 当前用户
            
        Raises:
            PermissionDenied: 当用户无权限时
        """
        # 验证权限（仅创建者可删除）
        if persona_card.uploader != user:
            raise PermissionDenied("只有创建者可以删除人设卡")
        
        # 删除关联的收藏记录
        StarRecord.objects.filter(
            target_id=str(persona_card.id),
            target_type='persona'
        ).delete()
        
        # 硬删除人设卡
        persona_card.delete()
    
    @staticmethod
    def submit_for_review(persona_card: PersonaCard, user: Users) -> None:
        """提交人设卡审核
        
        Args:
            persona_card: 人设卡对象
            user: 当前用户
            
        Raises:
            PermissionDenied: 当用户无权限时
            ValidationError: 当状态不允许提交或 TOML 验证失败时
        """
        # 验证权限（仅创建者可提交审核）
        if persona_card.uploader != user:
            raise PermissionDenied("只有创建者可以提交审核")
        
        # 验证状态（不能重复提交）
        if persona_card.is_pending:
            raise ValidationError("人设卡已处于待审核状态")
        
        # 验证 TOML 文件
        is_valid, error_msg = PersonaCardService.validate_toml_file(persona_card)
        if not is_valid:
            raise ValidationError(error_msg)
        
        # 更新状态
        persona_card.is_pending = True
        persona_card.is_public = False
        persona_card.save()
        
        # 更新上传记录
        UploadRecord.objects.filter(
            target_id=str(persona_card.id),
            target_type='persona'
        ).update(status='pending')

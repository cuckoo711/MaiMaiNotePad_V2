"""
收藏服务

提供收藏相关的业务逻辑，包括收藏、取消收藏、获取收藏列表和统计。
"""

from typing import Optional
from django.db.models import QuerySet
from django.core.exceptions import ValidationError

from mainotebook.system.models import Users
from ..models import StarRecord, KnowledgeBase, PersonaCard


class StarService:
    """收藏服务
    
    提供收藏相关的业务逻辑。
    """
    
    @staticmethod
    def star_content(user: Users, target_id: str, target_type: str) -> None:
        """收藏内容
        
        Args:
            user: 用户
            target_id: 目标 ID
            target_type: 目标类型（'knowledge' 或 'persona'）
            
        Raises:
            ValidationError: 当内容不存在、已收藏或目标类型无效时
        """
        # 验证目标类型
        if target_type not in ['knowledge', 'persona']:
            raise ValidationError("无效的目标类型")
        
        # 验证目标是否存在
        if target_type == 'knowledge':
            target = KnowledgeBase.objects.filter(id=target_id).first()
        else:  # target_type == 'persona'
            target = PersonaCard.objects.filter(id=target_id).first()
        
        if not target:
            raise ValidationError("内容不存在或已被删除")
        
        # 检查是否已收藏
        if StarRecord.objects.filter(user=user, target_id=target_id, target_type=target_type).exists():
            raise ValidationError("您已经收藏过该内容")
        
        # 创建收藏记录
        StarRecord.objects.create(
            user=user,
            target_id=target_id,
            target_type=target_type
        )
        
        # 增加收藏计数
        target.star_count += 1
        target.save(update_fields=['star_count'])
    
    @staticmethod
    def unstar_content(user: Users, target_id: str, target_type: str) -> None:
        """取消收藏内容
        
        Args:
            user: 用户
            target_id: 目标 ID
            target_type: 目标类型（'knowledge' 或 'persona'）
        """
        # 删除收藏记录
        deleted_count = StarRecord.objects.filter(
            user=user,
            target_id=target_id,
            target_type=target_type
        ).delete()[0]
        
        if deleted_count > 0:
            # 减少收藏计数
            if target_type == 'knowledge':
                target = KnowledgeBase.objects.filter(id=target_id).first()
            elif target_type == 'persona':
                target = PersonaCard.objects.filter(id=target_id).first()
            else:
                return
            
            if target:
                target.star_count = max(0, target.star_count - 1)
                target.save(update_fields=['star_count'])
    
    @staticmethod
    def get_user_stars(user: Users, target_type: Optional[str] = None) -> QuerySet:
        """获取用户收藏列表
        
        Args:
            user: 用户
            target_type: 目标类型（可选，'knowledge' 或 'persona'）
            
        Returns:
            QuerySet: 收藏记录查询集
        """
        queryset = StarRecord.objects.filter(user=user)
        
        if target_type:
            queryset = queryset.filter(target_type=target_type)
        
        return queryset.order_by('-create_datetime')
    
    @staticmethod
    def get_star_stats(user: Users) -> dict:
        """获取用户收藏统计
        
        Args:
            user: 用户
            
        Returns:
            dict: 收藏统计数据，包含总数和按类型分组的数量
        """
        total = StarRecord.objects.filter(user=user).count()
        knowledge_count = StarRecord.objects.filter(user=user, target_type='knowledge').count()
        persona_count = StarRecord.objects.filter(user=user, target_type='persona').count()
        
        return {
            'total': total,
            'knowledge': knowledge_count,
            'persona': persona_count
        }

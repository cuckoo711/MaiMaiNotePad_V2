# -*- coding: utf-8 -*-

"""
评论序列化器

提供评论相关的数据验证和序列化功能。
支持嵌套回复和树形结构返回。
"""

from rest_framework import serializers
from django.utils import timezone
from mainotebook.utils.serializers import CustomModelSerializer
from mainotebook.content.models import Comment, CommentReaction


class CommentSerializer(CustomModelSerializer):
    """评论序列化器
    
    用于评论列表和详情展示，支持嵌套回复。
    包含用户信息、回复列表、点赞状态等计算字段。
    """
    
    user_name = serializers.CharField(
        source='user.name',
        read_only=True,
        help_text="评论用户姓名"
    )
    user_avatar = serializers.CharField(
        source='user.avatar',
        read_only=True,
        allow_null=True,
        help_text="评论用户头像"
    )
    replies = serializers.SerializerMethodField(
        help_text="回复列表（嵌套结构）"
    )
    reply_to_name = serializers.SerializerMethodField(
        help_text="被回复人的用户名"
    )
    is_liked = serializers.SerializerMethodField(
        help_text="当前用户是否已点赞"
    )
    my_reaction = serializers.SerializerMethodField(
        help_text="当前用户的反应类型（like/dislike/null）"
    )
    
    class Meta:
        model = Comment
        fields = [
            'id', 'user', 'user_name', 'user_avatar', 'target_id',
            'target_type', 'parent', 'reply_to', 'reply_to_name',
            'content', 'is_deleted', 'moderation_status',
            'like_count', 'dislike_count', 'create_datetime',
            'update_datetime', 'replies', 'is_liked', 'my_reaction'
        ]
        read_only_fields = [
            'id', 'like_count', 'dislike_count', 'moderation_status',
            'create_datetime', 'update_datetime', 'user'
        ]
    
    def get_replies(self, obj):
        """获取回复列表（递归）
        
        Args:
            obj: Comment 实例
            
        Returns:
            list: 回复列表（嵌套结构）
        """
        # 如果已经预取了回复，使用预取的数据
        if hasattr(obj, '_prefetched_replies'):
            replies = obj._prefetched_replies
        else:
            # 否则查询数据库
            replies = obj.replies.filter(is_deleted=False).select_related('user')
        
        # 递归序列化回复
        return CommentSerializer(
            replies, 
            many=True, 
            context=self.context
        ).data
    
    def get_reply_to_name(self, obj):
        """获取被回复人的用户名
        
        通过 reply_to 关联动态查询用户名，用户改名后自动更新。
        
        Args:
            obj: Comment 实例
            
        Returns:
            str or None: 被回复人的用户名，无 reply_to 时返回 None
        """
        if obj.reply_to_id and obj.reply_to:
            return obj.reply_to.user.name if obj.reply_to.user else None
        return None
    
    def get_is_liked(self, obj):
        """判断当前用户是否已点赞
        
        Args:
            obj: Comment 实例
            
        Returns:
            bool: 是否已点赞
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return CommentReaction.objects.filter(
                user=request.user,
                comment=obj,
                reaction_type='like'
            ).exists()
        return False
    
    def get_my_reaction(self, obj):
        """获取当前用户对该评论的反应类型
        
        Args:
            obj: Comment 实例
            
        Returns:
            str or None: 反应类型（'like'、'dislike'）或 None
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            reaction = CommentReaction.objects.filter(
                user=request.user,
                comment=obj
            ).first()
            if reaction:
                return reaction.reaction_type
        return None


class CommentCreateSerializer(CustomModelSerializer):
    """评论创建序列化器
    
    用于创建评论和回复，包含完整的数据验证。
    """
    
    class Meta:
        model = Comment
        fields = ['target_id', 'target_type', 'parent', 'reply_to', 'content']
    
    def validate_content(self, value):
        """验证评论内容
        
        Args:
            value: 评论内容
            
        Returns:
            str: 验证通过的内容
            
        Raises:
            serializers.ValidationError: 当内容不符合要求时
        """
        if not value or not value.strip():
            raise serializers.ValidationError("评论内容不能为空")
        
        if len(value) > 500:
            raise serializers.ValidationError("评论内容不能超过 500 字符")
        
        return value
    
    def validate_parent(self, value):
        """验证父评论，并自动修正为根评论以保持两层结构
        
        如果传入的 parent 本身不是根评论（即它也有 parent），
        则沿 parent 链向上查找真正的根评论，确保评论树只有两层。
        
        Args:
            value: 父评论对象
            
        Returns:
            Comment: 验证通过的根评论对象
            
        Raises:
            serializers.ValidationError: 当父评论不存在或已被删除时
        """
        if value:
            # 检查父评论是否存在且未被删除
            if value.is_deleted:
                raise serializers.ValidationError("父评论已被删除")
            
            # 验证父评论是否真实存在于数据库中
            if not Comment.objects.filter(id=value.id, is_deleted=False).exists():
                raise serializers.ValidationError("父评论不存在")
            
            # 自动修正：如果 parent 不是根评论，沿链向上找到根评论
            current = value
            max_depth = 10  # 防止无限循环
            while current.parent_id and max_depth > 0:
                parent = Comment.objects.filter(
                    id=current.parent_id, is_deleted=False
                ).first()
                if not parent:
                    break
                current = parent
                max_depth -= 1
            value = current
        
        return value
    
    def validate(self, attrs):
        """验证用户是否被禁言
        
        Args:
            attrs: 待验证的属性字典
            
        Returns:
            dict: 验证通过的属性字典
            
        Raises:
            serializers.ValidationError: 当用户被禁言时
        """
        request = self.context.get('request')
        
        if not request:
            raise serializers.ValidationError("缺少请求上下文")
        
        user = request.user
        
        # 检查用户是否已认证
        if not user or not hasattr(user, 'id') or user.is_anonymous:
            raise serializers.ValidationError("用户未认证")
        
        # 检查用户是否被禁言
        if hasattr(user, 'is_muted') and user.is_muted:
            # 检查禁言是否仍然有效
            if hasattr(user, 'muted_until') and user.muted_until:
                if user.muted_until > timezone.now():
                    raise serializers.ValidationError("您已被禁言，无法发表评论")
        
        return attrs
    
    def create(self, validated_data):
        """创建评论，自动设置用户并执行 AI 内容审核
        
        评论内容会经过 AI 审核：
        - AI 通过或不确定：正常创建并展示
        - AI 拒绝：抛出异常，不创建评论
        
        Args:
            validated_data: 验证后的数据
            
        Returns:
            Comment: 创建的评论实例
            
        Raises:
            serializers.ValidationError: 当评论被 AI 审核拒绝时
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user:
            validated_data['user'] = request.user
        
        # AI 内容审核
        from mainotebook.content.services.comment_service import CommentService
        current_user = validated_data.get('user')
        moderation_status, moderation_detail = CommentService._moderate_content(
            validated_data.get('content', ''),
            user=current_user,
        )
        
        if moderation_status == 'rejected':
            # 将违规类型翻译为中文展示
            violation_label_map = {
                'porn': '色情内容',
                'politics': '涉政内容',
                'abuse': '辱骂内容',
            }
            import logging
            _logger = logging.getLogger(__name__)
            _logger.info("评论审核拒绝详情: %s", moderation_detail)
            violation_types = moderation_detail.get('violation_types', [])
            violation_labels = [violation_label_map.get(v, v) for v in violation_types]
            if violation_labels:
                msg = f"您的评论未通过内容审核（违规类型：{'、'.join(violation_labels)}），请修改后重试"
            else:
                msg = "您的评论未通过内容审核，请修改后重试"
            raise serializers.ValidationError(msg)
        
        validated_data['moderation_status'] = moderation_status
        validated_data['moderation_detail'] = moderation_detail
        
        return super().create(validated_data)

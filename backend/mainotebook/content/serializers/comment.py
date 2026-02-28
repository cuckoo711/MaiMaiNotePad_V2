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
            'content', 'is_deleted',
            'like_count', 'dislike_count', 'create_datetime',
            'update_datetime', 'replies', 'is_liked', 'my_reaction'
        ]
        read_only_fields = [
            'id', 'like_count', 'dislike_count', 
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
        """验证父评论
        
        Args:
            value: 父评论对象
            
        Returns:
            Comment: 验证通过的父评论对象
            
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
        """创建评论，自动设置用户
        
        Args:
            validated_data: 验证后的数据
            
        Returns:
            Comment: 创建的评论实例
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user:
            validated_data['user'] = request.user
        
        return super().create(validated_data)

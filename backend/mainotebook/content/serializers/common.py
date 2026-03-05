# -*- coding: utf-8 -*-

"""
通用序列化器

提供通用的序列化器基类和混入类，用于减少代码重复。
"""

from typing import Optional
from rest_framework import serializers
from mainotebook.utils.serializers import CustomModelSerializer
from mainotebook.content.models import StarRecord


class UploaderInfoMixin:
    """上传者信息混入类
    
    为序列化器添加上传者姓名和头像字段。
    适用于包含 uploader 外键的模型。
    """
    
    uploader_name = serializers.CharField(
        source='uploader.name',
        read_only=True,
        help_text="上传者姓名"
    )
    uploader_avatar = serializers.CharField(
        source='uploader.avatar',
        read_only=True,
        allow_null=True,
        help_text="上传者头像"
    )


class StarStatusMixin:
    """收藏状态混入类
    
    为序列化器添加收藏状态字段。
    需要在 Meta 中指定 target_type 属性。
    """
    
    is_starred = serializers.SerializerMethodField(
        help_text="当前用户是否已收藏"
    )
    
    def get_is_starred(self, obj) -> bool:
        """判断当前用户是否已收藏
        
        Args:
            obj: 模型实例
            
        Returns:
            bool: 是否已收藏
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        # 获取目标类型
        target_type = getattr(self.Meta, 'target_type', None)
        if not target_type:
            raise ValueError("StarStatusMixin 需要在 Meta 中指定 target_type 属性")
        
        return StarRecord.objects.filter(
            user=request.user,
            target_id=str(obj.id),
            target_type=target_type
        ).exists()


class UserInfoMixin:
    """用户信息混入类
    
    为序列化器添加用户姓名和头像字段。
    适用于包含 user 外键的模型（如评论）。
    """
    
    user_name = serializers.CharField(
        source='user.name',
        read_only=True,
        help_text="用户姓名"
    )
    user_avatar = serializers.CharField(
        source='user.avatar',
        read_only=True,
        allow_null=True,
        help_text="用户头像"
    )


class OwnershipValidationMixin:
    """所有权验证混入类
    
    提供通用的所有权验证方法。
    适用于需要验证用户是否为资源创建者的场景。
    """
    
    def validate_ownership(
        self, 
        instance, 
        user, 
        owner_field: str = 'uploader',
        error_message: str = "只有创建者可以执行此操作"
    ) -> None:
        """验证用户是否为资源所有者
        
        Args:
            instance: 模型实例
            user: 当前用户
            owner_field: 所有者字段名称，默认为 'uploader'
            error_message: 错误消息
            
        Raises:
            serializers.ValidationError: 当用户不是所有者时
        """
        owner = getattr(instance, owner_field, None)
        if owner != user:
            raise serializers.ValidationError(error_message)


class UniqueNameValidationMixin:
    """唯一名称验证混入类
    
    提供通用的名称唯一性验证方法。
    适用于需要在用户范围内验证名称唯一性的场景。
    """
    
    def validate_unique_name(
        self,
        value: str,
        user,
        model_class,
        owner_field: str = 'uploader',
        exclude_instance: Optional[object] = None,
        error_message: str = "您已经创建了同名的资源"
    ) -> str:
        """验证名称在用户范围内的唯一性
        
        Args:
            value: 名称值
            user: 当前用户
            model_class: 模型类
            owner_field: 所有者字段名称，默认为 'uploader'
            exclude_instance: 要排除的实例（用于更新时）
            error_message: 错误消息
            
        Returns:
            str: 验证通过的名称
            
        Raises:
            serializers.ValidationError: 当名称重复时
        """
        # 构建查询条件
        filter_kwargs = {
            owner_field: user,
            'name': value,
            'is_deleted': False
        }
        
        queryset = model_class.objects.filter(**filter_kwargs)
        
        # 如果是更新操作，排除当前实例
        if exclude_instance:
            queryset = queryset.exclude(id=exclude_instance.id)
        
        if queryset.exists():
            raise serializers.ValidationError(error_message)
        
        return value


class AuthenticationValidationMixin:
    """认证验证混入类
    
    提供通用的用户认证验证方法。
    """
    
    def validate_user_authenticated(self, request) -> None:
        """验证用户是否已认证
        
        Args:
            request: 请求对象
            
        Raises:
            serializers.ValidationError: 当用户未认证时
        """
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("用户未认证")


class ContentSerializer(
    UploaderInfoMixin,
    StarStatusMixin,
    CustomModelSerializer
):
    """内容序列化器基类
    
    为知识库和人设卡等内容类型提供通用的序列化功能。
    包含上传者信息、收藏状态等通用字段。
    
    子类需要：
    1. 在 Meta 中指定 target_type 属性（'knowledge' 或 'persona'）
    2. 实现 get_files 方法返回文件列表
    """
    
    files = serializers.SerializerMethodField(
        help_text="关联文件列表"
    )
    
    class Meta:
        # 子类需要覆盖这些属性
        model = None
        target_type = None  # 'knowledge' 或 'persona'
        fields = [
            'id', 'name', 'description', 'uploader', 'uploader_name',
            'uploader_avatar', 'copyright_owner', 'content', 'tags',
            'star_count', 'downloads', 'is_public', 'is_pending',
            'rejection_reason', 'version', 'create_datetime',
            'update_datetime', 'files', 'is_starred'
        ]
        read_only_fields = [
            'id', 'star_count', 'downloads', 'create_datetime',
            'update_datetime', 'uploader'
        ]
    
    def get_files(self, obj):
        """获取文件列表
        
        子类应该覆盖此方法以返回特定的文件序列化器。
        
        Args:
            obj: 模型实例
            
        Returns:
            list: 文件信息列表
        """
        raise NotImplementedError("子类必须实现 get_files 方法")


class ContentCreateSerializer(
    AuthenticationValidationMixin,
    UniqueNameValidationMixin,
    CustomModelSerializer
):
    """内容创建序列化器基类
    
    为知识库和人设卡等内容类型提供通用的创建功能。
    自动设置上传者，验证名称唯一性。
    
    子类需要：
    1. 在 Meta 中指定 model 和 fields
    2. 可选：覆盖 error_message_duplicate_name 自定义错误消息
    """
    
    # 子类可以覆盖此属性自定义错误消息
    error_message_duplicate_name = "您已经创建了同名的资源"
    
    class Meta:
        # 子类需要覆盖这些属性
        model = None
        fields = [
            'name', 'description', 'copyright_owner',
            'content', 'tags', 'version'
        ]
    
    def validate_name(self, value: str) -> str:
        """验证名称在用户范围内的唯一性
        
        Args:
            value: 名称值
            
        Returns:
            str: 验证通过的名称
            
        Raises:
            serializers.ValidationError: 当名称重复或用户未认证时
        """
        request = self.context.get('request')
        self.validate_user_authenticated(request)
        
        return self.validate_unique_name(
            value=value,
            user=request.user,
            model_class=self.Meta.model,
            error_message=self.error_message_duplicate_name
        )
    
    def create(self, validated_data):
        """创建内容，自动设置上传者
        
        Args:
            validated_data: 验证后的数据
            
        Returns:
            模型实例
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['uploader'] = request.user
        
        return super().create(validated_data)


class ContentUpdateSerializer(
    AuthenticationValidationMixin,
    OwnershipValidationMixin,
    UniqueNameValidationMixin,
    CustomModelSerializer
):
    """内容更新序列化器基类
    
    为知识库和人设卡等内容类型提供通用的更新功能。
    验证用户权限和名称唯一性。
    
    子类需要：
    1. 在 Meta 中指定 model 和 fields
    2. 可选：覆盖错误消息属性自定义错误消息
    """
    
    # 子类可以覆盖这些属性自定义错误消息
    error_message_permission_denied = "只有创建者可以修改资源"
    error_message_duplicate_name = "您已经创建了同名的资源"
    
    class Meta:
        # 子类需要覆盖这些属性
        model = None
        fields = [
            'name', 'description', 'copyright_owner',
            'content', 'tags', 'version'
        ]
    
    def validate(self, attrs):
        """验证权限
        
        Args:
            attrs: 待验证的属性字典
            
        Returns:
            dict: 验证通过的属性字典
            
        Raises:
            serializers.ValidationError: 当用户无权限时
        """
        request = self.context.get('request')
        self.validate_user_authenticated(request)
        
        self.validate_ownership(
            instance=self.instance,
            user=request.user,
            error_message=self.error_message_permission_denied
        )
        
        return attrs
    
    def validate_name(self, value: str) -> str:
        """验证名称在用户范围内的唯一性（排除当前实例）
        
        Args:
            value: 名称值
            
        Returns:
            str: 验证通过的名称
            
        Raises:
            serializers.ValidationError: 当名称重复或用户未认证时
        """
        request = self.context.get('request')
        self.validate_user_authenticated(request)
        
        return self.validate_unique_name(
            value=value,
            user=request.user,
            model_class=self.Meta.model,
            exclude_instance=self.instance,
            error_message=self.error_message_duplicate_name
        )


class FileSerializer(CustomModelSerializer):
    """文件序列化器基类
    
    为知识库文件和人设卡文件提供通用的序列化功能。
    
    子类需要：
    1. 在 Meta 中指定 model
    """
    
    class Meta:
        # 子类需要覆盖这些属性
        model = None
        fields = [
            'id', 'file_name', 'original_name', 'file_path',
            'file_type', 'file_size', 'create_datetime'
        ]
        read_only_fields = ['id', 'create_datetime']


class TagField(serializers.Field):
    """标签字段序列化器
    
    支持：
    1. 接收数组格式：["标签1", "标签2"]
    2. 接收字符串格式（向后兼容）："标签1,标签2"
    3. 自动去重、去空格
    4. 验证长度限制
    
    验证需求：3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8
    """
    
    MAX_TAG_LENGTH = 50
    MAX_TAGS_COUNT = 20
    
    def __init__(self, **kwargs):
        """初始化字段，设置默认值"""
        # 设置默认值为空列表，确保字段始终有值
        kwargs.setdefault('default', list)
        # 允许 None 值，但会在 to_internal_value 中转换为空列表
        kwargs.setdefault('allow_null', True)
        super().__init__(**kwargs)
    
    def to_internal_value(self, data):
        """将输入数据转换为标签数组
        
        Args:
            data: 标签数据，可以是数组、字符串或 None
            
        Returns:
            List[str]: 标准化的标签数组
            
        Raises:
            serializers.ValidationError: 验证失败时
        """
        # 处理 None 和空值
        if data is None or data == '':
            return []
        
        # 处理字符串格式（向后兼容）
        if isinstance(data, str):
            tags = [tag.strip() for tag in data.split(',') if tag.strip()]
        # 处理数组格式
        elif isinstance(data, list):
            tags = []
            for tag in data:
                if not isinstance(tag, str):
                    raise serializers.ValidationError(
                        f"标签必须是字符串类型，收到: {type(tag).__name__}"
                    )
                tag = tag.strip()
                if tag:
                    tags.append(tag)
        else:
            raise serializers.ValidationError(
                f"标签格式错误，必须是数组或字符串，收到: {type(data).__name__}"
            )
        
        # 去重（保持顺序）
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        
        # 验证单个标签长度
        for tag in unique_tags:
            if len(tag) > self.MAX_TAG_LENGTH:
                raise serializers.ValidationError(
                    f"标签 '{tag}' 超过最大长度 {self.MAX_TAG_LENGTH} 个字符"
                )
        
        # 验证标签数量
        if len(unique_tags) > self.MAX_TAGS_COUNT:
            raise serializers.ValidationError(
                f"标签数量超过最大限制 {self.MAX_TAGS_COUNT} 个"
            )
        
        return unique_tags
    
    def to_representation(self, value):
        """将数据库值转换为 API 响应格式
        
        同时进行标准化处理，确保输出始终是标准化的数组。
        
        Args:
            value: 数据库中的标签值
            
        Returns:
            List[str]: 标准化的标签数组
        """
        if value is None:
            return []
        
        # 如果数据库中还是字符串格式（迁移期间）
        if isinstance(value, str):
            tags = [tag.strip() for tag in value.split(',') if tag.strip()]
        # 已经是数组格式
        elif isinstance(value, list):
            tags = [tag.strip() for tag in value if tag and isinstance(tag, str)]
        else:
            return []
        
        # 去重（保持顺序）
        seen = set()
        unique_tags = []
        for tag in tags:
            tag = tag.strip()
            if tag and tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        
        return unique_tags

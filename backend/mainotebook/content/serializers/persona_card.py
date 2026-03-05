# -*- coding: utf-8 -*-

"""
人设卡序列化器

提供人设卡相关的数据验证和序列化功能。
"""

from rest_framework import serializers
from mainotebook.utils.serializers import CustomModelSerializer
from mainotebook.content.models import (
    PersonaCard, 
    PersonaCardFile, 
    PersonaCardConfig,
    SensitiveInfoConfirmation,
    StarRecord
)
from mainotebook.content.serializers.common import TagField


class PersonaCardFileSerializer(CustomModelSerializer):
    """人设卡文件序列化器
    
    用于序列化人设卡文件信息。
    """
    
    class Meta:
        model = PersonaCardFile
        fields = [
            'id', 'file_name', 'original_name', 'file_path', 
            'file_type', 'file_size', 'create_datetime'
        ]
        read_only_fields = ['id', 'create_datetime']


class PersonaCardSerializer(CustomModelSerializer):
    """人设卡列表序列化器
    
    用于列表和详情展示，包含关联数据和计算字段。
    """
    
    tags = TagField(required=False)
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
    files = serializers.SerializerMethodField(
        help_text="关联文件列表"
    )
    is_starred = serializers.SerializerMethodField(
        help_text="当前用户是否已收藏"
    )
    has_valid_toml = serializers.SerializerMethodField(
        help_text="是否包含有效的 bot_config.toml 文件"
    )
    comment_count = serializers.SerializerMethodField(
        help_text="评论数量"
    )
    
    class Meta:
        model = PersonaCard
        fields = [
            'id', 'name', 'description', 'uploader', 'uploader_name',
            'uploader_avatar', 'copyright_owner', 'content', 'tags',
            'star_count', 'downloads', 'is_public', 'is_pending',
            'rejection_reason', 'version', 'create_datetime',
            'update_datetime', 'files', 'is_starred', 'has_valid_toml',
            'comment_count'
        ]
        read_only_fields = [
            'id', 'star_count', 'downloads', 'create_datetime', 
            'update_datetime', 'uploader'
        ]
    
    def get_files(self, obj):
        """获取文件列表
        
        Args:
            obj: PersonaCard 实例
            
        Returns:
            list: 文件信息列表
        """
        return PersonaCardFileSerializer(
            obj.files.all(), 
            many=True
        ).data
    
    def get_is_starred(self, obj):
        """判断当前用户是否已收藏
        
        Args:
            obj: PersonaCard 实例
            
        Returns:
            bool: 是否已收藏
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return StarRecord.objects.filter(
                user=request.user,
                target_id=str(obj.id),
                target_type='persona'
            ).exists()
        return False
    
    def get_has_valid_toml(self, obj):
        """判断是否包含有效的 bot_config.toml 文件
        
        Args:
            obj: PersonaCard 实例
            
        Returns:
            bool: 是否包含且仅包含一个 bot_config.toml 文件
        """
        toml_files = obj.files.filter(original_name='bot_config.toml')
        return toml_files.count() == 1
    
    def get_comment_count(self, obj):
        """获取评论数量
        
        Args:
            obj: PersonaCard 实例
            
        Returns:
            int: 评论数量（包括所有层级的评论和回复）
        """
        from mainotebook.content.models import Comment
        return Comment.objects.filter(
            target_id=str(obj.id),
            target_type='persona',
            is_deleted=False
        ).count()
    
    def to_representation(self, instance):
        """序列化输出，隐藏非创建者的 content（补充说明）字段
        
        Args:
            instance: PersonaCard 实例
            
        Returns:
            dict: 序列化后的数据
        """
        data = super().to_representation(instance)
        request = self.context.get('request')
        # 非创建者不返回 content 字段
        if request and request.user.is_authenticated:
            if str(instance.uploader_id) != str(request.user.id):
                data['content'] = None
        else:
            data['content'] = None
        return data


class PersonaCardConfigSerializer(CustomModelSerializer):
    """人设卡配置项序列化器
    
    用于序列化配置项数据，包含配置块名、键名、值、数据类型、排序等信息。
    """
    
    class Meta:
        model = PersonaCardConfig
        fields = [
            'id', 'section_name', 'key_name', 'value', 
            'data_type', 'is_deleted', 'description',
            'section_order', 'item_order',
            'create_datetime', 'update_datetime'
        ]
        read_only_fields = ['id', 'create_datetime', 'update_datetime']
    
    def validate_value(self, value):
        """验证配置值
        
        Args:
            value: 配置值
            
        Returns:
            str: 验证通过的值
            
        Raises:
            serializers.ValidationError: 当值无效时
        """
        if value is None or value == '':
            raise serializers.ValidationError("配置值不能为空")
        return value


class SensitiveInfoConfirmationSerializer(CustomModelSerializer):
    """敏感信息确认记录序列化器
    
    用于序列化敏感信息确认记录，包含确认声明、敏感信息位置、IP 地址等。
    """
    
    class Meta:
        model = SensitiveInfoConfirmation
        fields = [
            'id', 'confirmation_text', 'sensitive_locations',
            'ip_address', 'confirmed_at'
        ]
        read_only_fields = ['id', 'ip_address', 'confirmed_at']
    
    def validate_confirmation_text(self, value):
        """验证确认声明文本
        
        Args:
            value: 确认声明文本
            
        Returns:
            str: 验证通过的文本
            
        Raises:
            serializers.ValidationError: 当文本格式不正确时
        """
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("确认声明至少需要 10 个字符")
        
        # 验证是否包含关键词
        if "确认" not in value or "隐私" not in value:
            raise serializers.ValidationError("确认声明必须包含'确认'和'隐私'关键词")
        
        return value.strip()
    
    def validate_sensitive_locations(self, value):
        """验证敏感信息位置
        
        Args:
            value: 敏感信息位置列表
            
        Returns:
            list: 验证通过的位置列表
            
        Raises:
            serializers.ValidationError: 当位置数据无效时
        """
        if not isinstance(value, list) or len(value) == 0:
            raise serializers.ValidationError("敏感信息位置必须是非空列表")
        
        return value


class PersonaCardCreateSerializer(CustomModelSerializer):
    """人设卡创建序列化器
    
    用于创建人设卡，自动设置上传者。
    接受 is_public 字段：为 True 时进入审核流程，否则为私有。
    支持配置项和敏感信息确认记录的创建。
    """
    
    tags = TagField(required=False)
    # 配置项列表（可选）
    configs = PersonaCardConfigSerializer(many=True, required=False)
    
    # 敏感信息确认记录（可选）
    sensitive_confirmation = SensitiveInfoConfirmationSerializer(required=False)
    
    class Meta:
        model = PersonaCard
        fields = [
            'name', 'description', 'copyright_owner', 
            'content', 'tags', 'is_public',
            'configs', 'sensitive_confirmation'
        ]
    
    def validate_name(self, value):
        """验证名称长度和唯一性
        
        Args:
            value: 人设卡名称
            
        Returns:
            str: 验证通过的名称
            
        Raises:
            serializers.ValidationError: 当名称不符合要求时
        """
        # 验证长度（1-200 个字符）
        if not value or len(value.strip()) < 1:
            raise serializers.ValidationError("名称不能为空")
        
        if len(value) > 200:
            raise serializers.ValidationError("名称长度不能超过 200 个字符")
        
        # HTML 转义处理
        import html
        value = html.escape(value.strip())
        
        # 验证用户范围内的唯一性
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("用户未认证")
        
        user = request.user
        if PersonaCard.objects.filter(
            uploader=user, 
            name=value
        ).exists():
            raise serializers.ValidationError("您已经创建了同名的人设卡")
        
        return value
    
    def validate_description(self, value):
        """验证描述最小长度
        
        Args:
            value: 人设卡描述
            
        Returns:
            str: 验证通过的描述
            
        Raises:
            serializers.ValidationError: 当描述不符合要求时
        """
        # 验证最小长度（至少 10 个字符）
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("描述至少需要 10 个字符")
        
        # HTML 转义处理
        import html
        value = html.escape(value.strip())
        
        return value
    
    def validate_copyright_owner(self, value):
        """验证版权所有者字段
        
        Args:
            value: 版权所有者
            
        Returns:
            str: 验证通过的版权所有者
        """
        if value:
            # HTML 转义处理
            import html
            value = html.escape(value.strip())
        
        return value
    
    def validate_content(self, value):
        """验证补充说明字段
        
        Args:
            value: 补充说明
            
        Returns:
            str: 验证通过的补充说明
        """
        if value:
            # HTML 转义处理
            import html
            value = html.escape(value.strip())
        
        return value
    
    def create(self, validated_data):
        """创建人设卡，自动设置上传者
        
        新创建的人设卡统一为私有未审核状态。
        如果用户选择了公开，由 perform_create 调用 submit_for_review 统一走审核流程。
        
        Args:
            validated_data: 验证后的数据
            
        Returns:
            PersonaCard: 创建的人设卡实例
        """
        # 提取嵌套数据
        configs_data = validated_data.pop('configs', [])
        sensitive_confirmation_data = validated_data.pop('sensitive_confirmation', None)
        
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['uploader'] = request.user
        
        # 新创建的人设卡统一为非待审核状态，审核由 submit_for_review 统一触发
        validated_data['is_pending'] = False
        # 暂存用户选择的公开意图，创建时先设为私有
        validated_data['is_public'] = False
        
        # 创建人设卡
        persona_card = super().create(validated_data)
        
        # 创建配置项
        if configs_data:
            from mainotebook.content.models import PersonaCardConfig
            config_instances = [
                PersonaCardConfig(
                    persona_card=persona_card,
                    **config_data
                )
                for config_data in configs_data
            ]
            PersonaCardConfig.objects.bulk_create(config_instances)
        
        # 创建敏感信息确认记录
        if sensitive_confirmation_data and request:
            from mainotebook.content.models import SensitiveInfoConfirmation
            SensitiveInfoConfirmation.objects.create(
                persona_card=persona_card,
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
                **sensitive_confirmation_data
            )
        
        return persona_card


class PersonaCardUpdateSerializer(CustomModelSerializer):
    """人设卡更新序列化器
    
    用于更新人设卡信息，验证权限。
    """
    
    tags = TagField(required=False)
    
    class Meta:
        model = PersonaCard
        fields = [
            'name', 'description', 'copyright_owner', 
            'content', 'tags'
        ]
        extra_kwargs = {
            'name': {'required': False},
            'description': {'required': False},
            'copyright_owner': {'required': False},
            'content': {'required': False},
            'tags': {'required': False},
        }
    
    def validate(self, attrs):
        """验证权限
        
        Args:
            attrs: 待验证的属性字典
            
        Returns:
            dict: 验证通过的属性字典
            
        Raises:
            serializers.ValidationError: 当用户无权限时
        """
        instance = self.instance
        request = self.context.get('request')
        
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("用户未认证")
        
        user = request.user
        if instance.uploader != user:
            raise serializers.ValidationError("只有创建者可以修改人设卡")
        
        return attrs
    
    def validate_name(self, value):
        """验证名称在用户范围内的唯一性（排除当前实例）
        
        Args:
            value: 人设卡名称
            
        Returns:
            str: 验证通过的名称
            
        Raises:
            serializers.ValidationError: 当名称重复时
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("用户未认证")
        
        user = request.user
        instance = self.instance
        
        # 检查是否存在同名人设卡（排除当前实例）
        if PersonaCard.objects.filter(
            uploader=user,
            name=value
        ).exclude(id=instance.id).exists():
            raise serializers.ValidationError("您已经创建了同名的人设卡")
        
        return value

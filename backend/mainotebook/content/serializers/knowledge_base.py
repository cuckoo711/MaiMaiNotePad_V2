# -*- coding: utf-8 -*-

"""
知识库序列化器

提供知识库相关的数据验证和序列化功能。
"""

from rest_framework import serializers
from mainotebook.utils.serializers import CustomModelSerializer
from mainotebook.content.models import KnowledgeBase, KnowledgeBaseFile, StarRecord


class KnowledgeBaseFileSerializer(CustomModelSerializer):
    """知识库文件序列化器
    
    用于序列化知识库文件信息。
    """
    
    class Meta:
        model = KnowledgeBaseFile
        fields = [
            'id', 'file_name', 'original_name', 'file_path', 
            'file_type', 'file_size', 'create_datetime'
        ]
        read_only_fields = ['id', 'create_datetime']


class KnowledgeBaseSerializer(CustomModelSerializer):
    """知识库列表序列化器
    
    用于列表和详情展示，包含关联数据和计算字段。
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
    files = serializers.SerializerMethodField(
        help_text="关联文件列表"
    )
    is_starred = serializers.SerializerMethodField(
        help_text="当前用户是否已收藏"
    )
    
    class Meta:
        model = KnowledgeBase
        fields = [
            'id', 'name', 'description', 'uploader', 'uploader_name',
            'uploader_avatar', 'copyright_owner', 'content', 'tags',
            'star_count', 'downloads', 'is_public', 'is_pending',
            'rejection_reason', 'create_datetime',
            'update_datetime', 'files', 'is_starred'
        ]
        read_only_fields = [
            'id', 'star_count', 'downloads', 'create_datetime', 
            'update_datetime', 'uploader'
        ]
    
    def get_files(self, obj):
        """获取文件列表
        
        Args:
            obj: KnowledgeBase 实例
            
        Returns:
            list: 文件信息列表
        """
        return KnowledgeBaseFileSerializer(
            obj.files.all(), 
            many=True
        ).data
    
    def get_is_starred(self, obj):
        """判断当前用户是否已收藏
        
        Args:
            obj: KnowledgeBase 实例
            
        Returns:
            bool: 是否已收藏
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return StarRecord.objects.filter(
                user=request.user,
                target_id=str(obj.id),
                target_type='knowledge'
            ).exists()
        return False

    def to_representation(self, instance):
        """序列化输出，隐藏非创建者的 content（补充说明）字段

        Args:
            instance: KnowledgeBase 实例

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



class KnowledgeBaseCreateSerializer(CustomModelSerializer):
    """知识库创建序列化器
    
    用于创建知识库，自动设置上传者。
    接受 is_public 字段：为 True 时进入审核流程，否则为私有。
    """
    
    class Meta:
        model = KnowledgeBase
        fields = [
            'name', 'description', 'copyright_owner', 
            'content', 'tags', 'is_public'
        ]
    
    def validate_name(self, value):
        """验证名称在用户范围内的唯一性
        
        Args:
            value: 知识库名称
            
        Returns:
            str: 验证通过的名称
            
        Raises:
            serializers.ValidationError: 当名称重复时
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("用户未认证")
        
        user = request.user
        if KnowledgeBase.objects.filter(
            uploader=user, 
            name=value
        ).exists():
            raise serializers.ValidationError("您已经创建了同名的知识库")
        
        return value
    
    def create(self, validated_data):
        """创建知识库，自动设置上传者和审核状态
        
        根据 is_public 决定审核状态：
        - is_public=True: 进入审核流程（is_pending=True）
        - is_public=False 或未传: 私有（is_pending=False）
        
        Args:
            validated_data: 验证后的数据
            
        Returns:
            KnowledgeBase: 创建的知识库实例
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['uploader'] = request.user
        
        # 私有内容不需要审核
        is_public = validated_data.get('is_public', False)
        if not is_public:
            validated_data['is_pending'] = False
        
        return super().create(validated_data)


class KnowledgeBaseUpdateSerializer(CustomModelSerializer):
    """知识库更新序列化器
    
    用于更新知识库信息，验证权限。
    """
    
    class Meta:
        model = KnowledgeBase
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
            raise serializers.ValidationError("只有创建者可以修改知识库")
        
        return attrs
    
    def validate_name(self, value):
        """验证名称在用户范围内的唯一性（排除当前实例）
        
        Args:
            value: 知识库名称
            
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
        
        # 检查是否存在同名知识库（排除当前实例）
        if KnowledgeBase.objects.filter(
            uploader=user,
            name=value
        ).exclude(id=instance.id).exists():
            raise serializers.ValidationError("您已经创建了同名的知识库")
        
        return value

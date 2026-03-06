# -*- coding: utf-8 -*-

"""
@Remark: 翻译管理
"""
from rest_framework import serializers

from mainotebook.system.models import Translation
from mainotebook.utils.serializers import CustomModelSerializer


class TranslationSerializer(CustomModelSerializer):
    """翻译序列化器
    
    用于翻译数据的验证、序列化和反序列化。
    """
    
    class Meta:
        model = Translation
        fields = [
            'id', 'source_text', 'translated_text',
            'source_language', 'target_language',
            'translation_type', 'sort', 'status',
            'create_datetime', 'update_datetime'
        ]
        read_only_fields = ['id', 'create_datetime', 'update_datetime']
    
    def validate_source_text(self, value: str) -> str:
        """验证原文字段
        
        Args:
            value: 原文字符串
            
        Returns:
            str: 去除首尾空格后的原文
            
        Raises:
            serializers.ValidationError: 当原文为空或超过长度限制时
        """
        if not value or not value.strip():
            raise serializers.ValidationError("原文不能为空")
        if len(value) > 200:
            raise serializers.ValidationError("原文长度不能超过 200 个字符")
        return value.strip()
    
    def validate_translated_text(self, value: str) -> str:
        """验证译文字段
        
        Args:
            value: 译文字符串
            
        Returns:
            str: 去除首尾空格后的译文
            
        Raises:
            serializers.ValidationError: 当译文为空或超过长度限制时
        """
        if not value or not value.strip():
            raise serializers.ValidationError("译文不能为空")
        if len(value) > 200:
            raise serializers.ValidationError("译文长度不能超过 200 个字符")
        return value.strip()
    
    def validate_translation_type(self, value: str) -> str:
        """验证翻译类型字段
        
        Args:
            value: 翻译类型字符串
            
        Returns:
            str: 去除首尾空格后的翻译类型
            
        Raises:
            serializers.ValidationError: 当翻译类型为空或超过长度限制时
        """
        if not value or not value.strip():
            raise serializers.ValidationError("翻译类型不能为空")
        if len(value) > 50:
            raise serializers.ValidationError("翻译类型长度不能超过 50 个字符")
        return value.strip()
    
    def validate_source_language(self, value: str) -> str:
        """验证源语言字段
        
        Args:
            value: 源语言代码字符串
            
        Returns:
            str: 去除首尾空格后的源语言代码
            
        Raises:
            serializers.ValidationError: 当源语言代码为空或超过长度限制时
        """
        if not value or not value.strip():
            raise serializers.ValidationError("源语言不能为空")
        if len(value) > 10:
            raise serializers.ValidationError("源语言长度不能超过 10 个字符")
        return value.strip()
    
    def validate_target_language(self, value: str) -> str:
        """验证目标语言字段
        
        Args:
            value: 目标语言代码字符串
            
        Returns:
            str: 去除首尾空格后的目标语言代码
            
        Raises:
            serializers.ValidationError: 当目标语言代码为空或超过长度限制时
        """
        if not value or not value.strip():
            raise serializers.ValidationError("目标语言不能为空")
        if len(value) > 10:
            raise serializers.ValidationError("目标语言长度不能超过 10 个字符")
        return value.strip()
    
    def validate(self, attrs: dict) -> dict:
        """验证唯一性约束
        
        检查在相同翻译类型下是否已存在相同的原文。
        
        Args:
            attrs: 验证后的属性字典
            
        Returns:
            dict: 验证通过的属性字典
            
        Raises:
            serializers.ValidationError: 当存在重复的翻译记录时
        """
        translation_type = attrs.get('translation_type')
        source_text = attrs.get('source_text')
        
        # 更新时排除当前实例
        queryset = Translation.objects.filter(
            translation_type=translation_type,
            source_text=source_text
        )
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        
        if queryset.exists():
            raise serializers.ValidationError(
                "该翻译类型下已存在相同的原文"
            )
        
        return attrs


from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from mainotebook.utils.viewset import CustomModelViewSet


class TranslationViewSet(CustomModelViewSet):
    """翻译视图集
    
    提供翻译数据的 CRUD 操作和自定义查询接口。
    """
    queryset = Translation.objects.all()
    serializer_class = TranslationSerializer
    filterset_fields = ['translation_type', 'source_language', 'target_language', 'status']
    search_fields = ['source_text', 'translated_text']
    ordering_fields = ['sort', 'create_datetime']
    ordering = ['sort']
    # 禁用数据权限过滤，因为翻译数据是公开的
    extra_filter_class = []
    # 使用 get_permissions() 方法动态设置权限，这里设置一个占位符
    # 注意：不能设置为 []，否则 DRF 会跳过权限检查
    permission_classes = [AllowAny]  # 这个会被 get_permissions() 覆盖
    
    def get_permissions(self):
        """获取权限类
        
        查询操作允许公开访问，修改操作需要管理员权限。
        
        Returns:
            list: 权限类实例列表
        """
        if self.action in ['list', 'retrieve', 'get_by_type', 'get_types']:
            # 查询操作允许公开访问
            return [AllowAny()]
        # 修改操作需要管理员权限（IsAdminUser 已经包含了 IsAuthenticated 的检查）
        return [IsAuthenticated(), IsAdminUser()]
    
    @action(detail=False, methods=['get'], url_path='get_types')
    def get_types(self, request):
        """获取所有翻译类型、源语言和目标语言
        
        返回数据库中所有不重复的翻译类型、源语言和目标语言列表。
        
        Args:
            request: HTTP 请求对象
            
        Returns:
            Response: 包含翻译类型、源语言和目标语言列表的响应
        """
        # 获取所有不重复的翻译类型
        translation_types = Translation.objects.values_list('translation_type', flat=True).distinct().order_by('translation_type')
        
        # 获取所有不重复的源语言
        source_languages = Translation.objects.values_list('source_language', flat=True).distinct().order_by('source_language')
        
        # 获取所有不重复的目标语言
        target_languages = Translation.objects.values_list('target_language', flat=True).distinct().order_by('target_language')
        
        # 转换为字典列表格式，符合前端 dict-select 组件的要求
        data = {
            'translation_types': [{'label': t, 'value': t} for t in translation_types if t],
            'source_languages': [{'label': lang, 'value': lang} for lang in source_languages if lang],
            'target_languages': [{'label': lang, 'value': lang} for lang in target_languages if lang]
        }
        
        return Response({
            'code': 2000,
            'msg': '获取成功',
            'data': data
        })
    
    @action(detail=False, methods=['get'], url_path='get_by_type')
    def get_by_type(self, request):
        """按类型查询翻译
        
        Args:
            request: HTTP 请求对象，包含 translation_type 参数
            
        Returns:
            Response: 包含翻译列表的响应
        """
        translation_type = request.query_params.get('translation_type')
        
        if not translation_type:
            return Response(
                {'error': '缺少 translation_type 参数'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(
            translation_type=translation_type,
            status=True
        ).order_by('sort')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

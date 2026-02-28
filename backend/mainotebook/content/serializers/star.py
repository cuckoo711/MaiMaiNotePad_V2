# -*- coding: utf-8 -*-

"""
收藏序列化器

提供收藏记录相关的数据验证和序列化功能。
"""

from typing import Optional, Dict, Any, Union
from rest_framework import serializers
from mainotebook.utils.serializers import CustomModelSerializer
from mainotebook.content.models import StarRecord, KnowledgeBase, PersonaCard


class StarRecordSerializer(CustomModelSerializer):
    """收藏记录序列化器
    
    用于收藏列表展示，包含目标对象的基本信息。
    """
    
    target_name = serializers.SerializerMethodField(
        help_text="目标名称"
    )
    target_description = serializers.SerializerMethodField(
        help_text="目标描述"
    )
    target_creator = serializers.SerializerMethodField(
        help_text="目标创建者信息"
    )
    target_detail = serializers.SerializerMethodField(
        help_text="目标详情"
    )
    
    class Meta:
        model = StarRecord
        fields = [
            'id', 'target_id', 'target_type', 'target_name',
            'target_description', 'target_creator', 'create_datetime',
            'target_detail'
        ]
        read_only_fields = ['id', 'create_datetime']
    
    def get_target_detail(self, obj: StarRecord) -> Optional[Dict[str, Any]]:
        """获取目标详情
        
        Args:
            obj: StarRecord 对象
            
        Returns:
            dict: 目标详情字典，包含完整的目标对象信息
                  如果目标不存在则返回 None
        """
        target = self._get_target(obj)
        if not target:
            return None
            
        if obj.target_type == 'knowledge':
            from mainotebook.content.serializers.knowledge_base import KnowledgeBaseSerializer
            return KnowledgeBaseSerializer(target, context=self.context).data
        elif obj.target_type == 'persona':
            from mainotebook.content.serializers.persona_card import PersonaCardSerializer
            return PersonaCardSerializer(target, context=self.context).data
        return None
    
    def get_target_name(self, obj: StarRecord) -> Optional[str]:
        """获取目标名称
        
        Args:
            obj: StarRecord 对象
            
        Returns:
            str: 目标名称，如果目标不存在则返回 None
        """
        target = self._get_target(obj)
        return target.name if target else None
    
    def get_target_description(self, obj: StarRecord) -> Optional[str]:
        """获取目标描述
        
        Args:
            obj: StarRecord 对象
            
        Returns:
            str: 目标描述，如果目标不存在则返回 None
        """
        target = self._get_target(obj)
        return target.description if target else None
    
    def get_target_creator(self, obj: StarRecord) -> Optional[Dict[str, Any]]:
        """获取目标创建者信息
        
        Args:
            obj: StarRecord 对象
            
        Returns:
            dict: 创建者信息字典，包含 id、name、avatar 字段
                  如果目标不存在则返回 None
        """
        target = self._get_target(obj)
        if target:
            return {
                'id': target.uploader.id,
                'name': target.uploader.name,
                'avatar': target.uploader.avatar
            }
        return None
    
    def _get_target(self, obj: StarRecord) -> Optional[Union[KnowledgeBase, PersonaCard]]:
        """获取目标对象
        
        根据 target_type 查询对应的知识库或人设卡对象。
        
        Args:
            obj: StarRecord 对象
            
        Returns:
            KnowledgeBase | PersonaCard | None: 目标对象，如果不存在则返回 None
        """
        if obj.target_type == 'knowledge':
            return KnowledgeBase.objects.filter(id=obj.target_id).first()
        elif obj.target_type == 'persona':
            return PersonaCard.objects.filter(id=obj.target_id).first()
        return None

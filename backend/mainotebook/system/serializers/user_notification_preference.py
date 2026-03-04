# -*- coding: utf-8 -*-

"""
用户通知偏好序列化器
"""

from rest_framework import serializers
from mainotebook.system.models import UserNotificationPreference
from mainotebook.utils.serializers import CustomModelSerializer


class UserNotificationPreferenceSerializer(CustomModelSerializer):
    """用户通知偏好序列化器"""
    
    message_type_display = serializers.SerializerMethodField(read_only=True)
    
    def get_message_type_display(self, obj):
        """获取消息类型的显示名称"""
        type_names = {
            0: '系统通知',
            1: '评论',
            2: '回复',
            3: '点赞',
            4: '审核'
        }
        return type_names.get(obj.message_type, '未知')
    
    def validate_message_type(self, value):
        """验证消息类型
        
        只有评论(1)、回复(2)、点赞(3)可以设置免打扰。
        系统通知(0)和审核通知(4)不允许设置免打扰。
        """
        if value in [0, 4]:
            raise serializers.ValidationError("系统通知和审核通知不可设置免打扰")
        if value not in [1, 2, 3]:
            raise serializers.ValidationError("无效的消息类型")
        return value
    
    class Meta:
        model = UserNotificationPreference
        fields = ['id', 'user', 'message_type', 'message_type_display', 
                  'is_muted', 'muted_at', 'create_datetime', 'update_datetime']
        read_only_fields = ['id', 'create_datetime', 'update_datetime', 'muted_at']

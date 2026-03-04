# -*- coding: utf-8 -*-

"""
用户通知偏好视图集
"""

from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from mainotebook.system.models import UserNotificationPreference, MessageCenterTargetUser
from mainotebook.system.serializers.user_notification_preference import UserNotificationPreferenceSerializer
from mainotebook.utils.json_response import DetailResponse, ErrorResponse
from mainotebook.utils.viewset import CustomModelViewSet


class UserNotificationPreferenceViewSet(CustomModelViewSet):
    """用户通知偏好接口
    
    提供用户通知偏好的查询和设置功能。
    所有接口都只需要登录权限，不需要特殊权限。
    """
    queryset = UserNotificationPreference.objects.all()
    serializer_class = UserNotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """只返回当前用户的通知偏好"""
        return UserNotificationPreference.objects.filter(user=self.request.user)
    
    @action(methods=['GET'], detail=False, permission_classes=[IsAuthenticated])
    def get_preferences(self, request):
        """获取当前用户的所有通知偏好
        
        Returns:
            包含各消息类型免打扰状态的字典
        """
        user_id = request.user.id
        preferences = UserNotificationPreference.objects.filter(user_id=user_id)
        
        # 构建返回数据：message_type -> is_muted
        result = {}
        for pref in preferences:
            result[pref.message_type] = {
                'is_muted': pref.is_muted,
                'muted_at': pref.muted_at
            }
        
        return DetailResponse(data=result, msg="获取成功")
    
    @action(methods=['POST'], detail=False, permission_classes=[IsAuthenticated])
    def set_mute(self, request):
        """设置某类消息为免打扰
        
        Request Body:
            message_type (int): 消息类型（1=评论, 2=回复, 3=点赞）
            
        Returns:
            设置结果
        """
        user_id = request.user.id
        message_type = request.data.get('message_type')
        
        if message_type is None:
            return ErrorResponse(msg="缺少 message_type 参数")
        
        try:
            message_type = int(message_type)
        except (ValueError, TypeError):
            return ErrorResponse(msg="message_type 必须是整数")
        
        # 系统通知和审核通知不允许免打扰
        if message_type in [0, 4]:
            return ErrorResponse(msg="系统通知和审核通知不可设置免打扰")
        
        if message_type not in [1, 2, 3]:
            return ErrorResponse(msg="无效的消息类型")
        
        # 获取或创建偏好记录
        preference, created = UserNotificationPreference.objects.get_or_create(
            user_id=user_id,
            message_type=message_type,
            defaults={
                'is_muted': True,
                'muted_at': timezone.now()
            }
        )
        
        if not created and not preference.is_muted:
            # 如果已存在但未免打扰，则更新为免打扰
            preference.is_muted = True
            preference.muted_at = timezone.now()
            preference.save()
        
        # 将该类型的所有未读消息标记为已读
        from mainotebook.system.views.message_center import MessageCenterViewSet
        visible_messages = MessageCenterViewSet._get_user_visible_queryset(user_id).filter(
            message_type=message_type
        )
        visible_msg_ids = list(visible_messages.values_list('id', flat=True))
        
        if visible_msg_ids:
            # 获取已有的中间表记录
            existing_records = MessageCenterTargetUser.objects.filter(
                users_id=user_id,
                messagecenter_id__in=visible_msg_ids
            )
            
            # 更新已有记录为已读
            existing_records.update(is_read=True)
            
            # 找出没有中间表记录的消息
            existing_msg_ids = set(existing_records.values_list('messagecenter_id', flat=True))
            missing_msg_ids = set(visible_msg_ids) - existing_msg_ids
            
            # 为缺失的消息创建已读记录
            if missing_msg_ids:
                new_records = [
                    MessageCenterTargetUser(
                        users_id=user_id,
                        messagecenter_id=msg_id,
                        is_read=True
                    )
                    for msg_id in missing_msg_ids
                ]
                MessageCenterTargetUser.objects.bulk_create(new_records)
        
        type_names = {1: '评论', 2: '回复', 3: '点赞'}
        type_name = type_names.get(message_type, '未知类型')
        
        return DetailResponse(
            data={
                'message_type': message_type,
                'is_muted': True,
                'marked_read_count': len(visible_msg_ids)
            },
            msg=f"{type_name}通知已设置为免打扰"
        )
    
    @action(methods=['POST'], detail=False, permission_classes=[IsAuthenticated])
    def cancel_mute(self, request):
        """取消某类消息的免打扰
        
        Request Body:
            message_type (int): 消息类型（1=评论, 2=回复, 3=点赞）
            
        Returns:
            取消结果
        """
        user_id = request.user.id
        message_type = request.data.get('message_type')
        
        if message_type is None:
            return ErrorResponse(msg="缺少 message_type 参数")
        
        try:
            message_type = int(message_type)
        except (ValueError, TypeError):
            return ErrorResponse(msg="message_type 必须是整数")
        
        if message_type not in [1, 2, 3]:
            return ErrorResponse(msg="无效的消息类型")
        
        # 查找偏好记录
        try:
            preference = UserNotificationPreference.objects.get(
                user_id=user_id,
                message_type=message_type
            )
            preference.is_muted = False
            preference.save()
            
            type_names = {1: '评论', 2: '回复', 3: '点赞'}
            type_name = type_names.get(message_type, '未知类型')
            
            return DetailResponse(
                data={
                    'message_type': message_type,
                    'is_muted': False
                },
                msg=f"{type_name}通知已取消免打扰"
            )
        except UserNotificationPreference.DoesNotExist:
            return DetailResponse(
                data={
                    'message_type': message_type,
                    'is_muted': False
                },
                msg="该消息类型未设置免打扰"
            )

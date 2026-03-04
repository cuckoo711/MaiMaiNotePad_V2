# -*- coding: utf-8 -*-
"""消息中心视图

消息投递架构：
- target_type=0: 指定用户，通过中间表 MessageCenterTargetUser 关联
- target_type=1: 按角色，通过 target_role 字段存储目标角色，查询时动态匹配
- target_type=2: 按部门，通过 target_dept 字段存储目标部门，查询时动态匹配
- target_type=3: 系统通知（全员），查询时直接返回给所有用户

已读状态统一采用懒创建：中间表仅在用户查看消息时才创建记录并标记已读。
"""
import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Q
from django_restql.fields import DynamicSerializerMethodField
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from mainotebook.system.models import MessageCenter, Users, MessageCenterTargetUser, UserNotificationPreference
from mainotebook.utils.json_response import SuccessResponse, DetailResponse
from mainotebook.utils.serializers import CustomModelSerializer
from mainotebook.utils.viewset import CustomModelViewSet


class MessageCenterSerializer(CustomModelSerializer):
    """消息中心-序列化器（管理端，用于 list/create 等）"""
    role_info = DynamicSerializerMethodField()
    user_info = DynamicSerializerMethodField()
    dept_info = DynamicSerializerMethodField()
    is_read = serializers.BooleanField(read_only=True, source='target_user__is_read')

    def get_role_info(self, instance, parsed_query):
        """获取目标角色信息"""
        roles = instance.target_role.all()
        from mainotebook.system.views.role import RoleSerializer
        serializer = RoleSerializer(roles, many=True, parsed_query=parsed_query)
        return serializer.data

    def get_user_info(self, instance, parsed_query):
        """获取目标用户信息（仅 target_type=0 时返回）"""
        if instance.target_type in (1, 2, 3):
            return []
        users = instance.target_user.all()
        from mainotebook.system.views.user import UserSerializer
        serializer = UserSerializer(users, many=True, parsed_query=parsed_query)
        return serializer.data

    def get_dept_info(self, instance, parsed_query):
        """获取目标部门信息"""
        dept = instance.target_dept.all()
        from mainotebook.system.views.dept import DeptSerializer
        serializer = DeptSerializer(dept, many=True, parsed_query=parsed_query)
        return serializer.data

    class Meta:
        model = MessageCenter
        fields = "__all__"
        read_only_fields = ["id"]


class MessageCenterTargetUserSerializer(CustomModelSerializer):
    """目标用户中间表-序列化器"""

    class Meta:
        model = MessageCenterTargetUser
        fields = "__all__"
        read_only_fields = ["id"]


class MessageCenterTargetUserListSerializer(CustomModelSerializer):
    """消息列表-序列化器（用户端，用于 get_self_receive）"""
    role_info = DynamicSerializerMethodField()
    user_info = DynamicSerializerMethodField()
    dept_info = DynamicSerializerMethodField()
    is_read = serializers.SerializerMethodField()

    def get_is_read(self, instance):
        """获取当前用户对该消息的已读状态
        
        中间表无记录时视为未读（懒创建模式）
        """
        user_id = self.request.user.id
        record = MessageCenterTargetUser.objects.filter(
            messagecenter__id=instance.id, users_id=user_id
        ).first()
        return record.is_read if record else False

    def get_role_info(self, instance, parsed_query):
        """获取目标角色信息"""
        roles = instance.target_role.all()
        from mainotebook.system.views.role import RoleSerializer
        serializer = RoleSerializer(roles, many=True, parsed_query=parsed_query)
        return serializer.data

    def get_user_info(self, instance, parsed_query):
        """获取目标用户信息（仅 target_type=0 时返回）"""
        if instance.target_type in (1, 2, 3):
            return []
        users = instance.target_user.all()
        from mainotebook.system.views.user import UserSerializer
        serializer = UserSerializer(users, many=True, parsed_query=parsed_query)
        return serializer.data

    def get_dept_info(self, instance, parsed_query):
        """获取目标部门信息"""
        dept = instance.target_dept.all()
        from mainotebook.system.views.dept import DeptSerializer
        serializer = DeptSerializer(dept, many=True, parsed_query=parsed_query)
        return serializer.data

    class Meta:
        model = MessageCenter
        fields = "__all__"
        read_only_fields = ["id"]


class MessageCenterDetailSerializer(CustomModelSerializer):
    """消息详情-序列化器（用户端，用于 retrieve 获取完整内容）
    
    与列表序列化器的区别：
    - 返回完整的 content 字段，不进行截断
    - 返回完整的 extra_data 字段
    - 用于消息详情弹窗展示
    """
    is_read = serializers.SerializerMethodField()

    def get_is_read(self, instance):
        """获取当前用户对该消息的已读状态
        
        中间表无记录时视为未读（懒创建模式）
        """
        user_id = self.request.user.id
        record = MessageCenterTargetUser.objects.filter(
            messagecenter__id=instance.id, users_id=user_id
        ).first()
        return record.is_read if record else False

    class Meta:
        model = MessageCenter
        fields = [
            'id', 'title', 'content', 'message_type', 'target_type',
            'create_datetime', 'update_datetime', 'extra_data', 'is_read'
        ]
        read_only_fields = ["id"]


def websocket_push(user_id, message):
    """通过 WebSocket 向指定用户推送消息
    
    Args:
        user_id: 目标用户 ID
        message: 推送消息体字典
    """
    username = "user_" + str(user_id)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        username,
        {"type": "push.message", "json": message}
    )


def _broadcast_websocket(user_ids, message):
    """批量 WebSocket 推送
    
    Args:
        user_ids: 用户 ID 可迭代对象
        message: 推送消息体字典
    """
    channel_layer = get_channel_layer()
    for uid in user_ids:
        async_to_sync(channel_layer.group_send)(
            "user_" + str(uid),
            {"type": "push.message", "json": message}
        )


class MessageCenterCreateSerializer(CustomModelSerializer):
    """消息中心-新增-序列化器
    
    创建消息时的投递策略：
    - target_type=0（指定用户）：写入中间表，逐个推送
    - target_type=1（按角色）：仅保存 target_role，不写中间表，WebSocket 通知在线用户
    - target_type=2（按部门）：仅保存 target_dept，不写中间表，WebSocket 通知在线用户
    - target_type=3（系统通知）：不写中间表，WebSocket 广播所有在线用户
    """

    def save(self, **kwargs):
        """保存消息并根据 target_type 执行不同的投递策略
        
        创建消息时会检查用户的免打扰偏好：
        - 如果用户对该类型消息设置了免打扰，则自动标记为已读
        - 系统通知（message_type=0）不受免打扰影响
        """
        data = super().save(**kwargs)
        initial_data = self.initial_data
        target_type = initial_data.get('target_type')
        message_type = initial_data.get('message_type', 0)
        ws_message = {"sender": "system", "contentType": "SYSTEM",
                      "content": "您有一条新消息~", "unread": 1}

        if target_type == 0:
            # 指定用户：写入中间表并逐个推送
            users = initial_data.get('target_user', [])
            
            # 查询这些用户中哪些设置了该类型消息的免打扰
            muted_users = set()
            if message_type not in [0, 4]:  # 系统通知和审核通知不受免打扰影响
                muted_prefs = UserNotificationPreference.objects.filter(
                    user_id__in=users,
                    message_type=message_type,
                    is_muted=True
                ).values_list('user_id', flat=True)
                muted_users = set(muted_prefs)
            
            # 为所有用户创建中间表记录
            targetuser_data = []
            for uid in users:
                # 如果用户设置了免打扰，直接标记为已读
                is_read = uid in muted_users
                targetuser_data.append({
                    "messagecenter": data.id,
                    "users": uid,
                    "is_read": is_read
                })
            
            targetuser_instance = MessageCenterTargetUserSerializer(
                data=targetuser_data, many=True, request=self.request
            )
            targetuser_instance.is_valid(raise_exception=True)
            targetuser_instance.save()
            
            # 推送 WebSocket 通知（只推送给未免打扰的用户）
            for uid in users:
                if uid not in muted_users:
                    unread_count = MessageCenterTargetUser.objects.filter(
                        users__id=uid, is_read=False
                    ).count()
                    websocket_push(uid, message={**ws_message, "unread": unread_count})
                    
        elif target_type == 1:
            # 按角色：不写中间表，推送给角色下的在线用户
            target_role = initial_data.get('target_role', [])
            user_ids = Users.objects.filter(
                role__id__in=target_role
            ).values_list('id', flat=True).distinct()
            _broadcast_websocket(user_ids, ws_message)
            
        elif target_type == 2:
            # 按部门：不写中间表，推送给部门下的在线用户
            target_dept = initial_data.get('target_dept', [])
            user_ids = Users.objects.filter(
                dept__id__in=target_dept
            ).values_list('id', flat=True).distinct()
            _broadcast_websocket(user_ids, ws_message)
            
        elif target_type == 3:
            # 系统通知：不写中间表，广播所有在线用户
            user_ids = Users.objects.values_list('id', flat=True)
            _broadcast_websocket(user_ids, ws_message)

        return data

    class Meta:
        model = MessageCenter
        fields = "__all__"
        read_only_fields = ["id"]


class MessageCenterViewSet(CustomModelViewSet):
    """消息中心接口

    list: 查询当前用户创建的消息
    create: 新增消息
    retrieve: 查看消息详情（同时标记已读）
    get_self_receive: 获取当前用户接收到的消息
    get_newest_msg: 获取最新一条消息
    """
    queryset = MessageCenter.objects.order_by('create_datetime')
    serializer_class = MessageCenterSerializer
    create_serializer_class = MessageCenterCreateSerializer
    extra_filter_backends = []
    # 前台用户可能没有部门，禁用后台数据级权限过滤，避免返回 400
    extra_filter_class = []

    def get_permissions(self):
        """根据 action 动态返回权限类
        
        retrieve 操作（标记已读）只需要登录即可，普通用户也能使用。
        其他操作走默认的 dvadmin 按钮权限检查。
        """
        if self.action == 'retrieve':
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        """管理端 list 只返回当前用户创建的消息"""
        if self.action == 'list':
            return MessageCenter.objects.filter(creator=self.request.user.id).all()
        return MessageCenter.objects.all()

    def retrieve(self, request, *args, **kwargs):
        """查看消息详情并标记已读
        
        所有类型的消息统一采用懒创建：用户首次查看时创建中间表记录并标记已读。
        如果用户对该类型消息设置了免打扰，懒创建时也会自动标记为已读。
        使用 MessageCenterDetailSerializer 返回完整的消息内容。
        """
        pk = kwargs.get('pk')
        user_id = self.request.user.id
        instance = self.get_object()

        # 查找或懒创建已读记录
        target_record = MessageCenterTargetUser.objects.filter(
            users__id=user_id, messagecenter__id=pk
        ).first()
        
        if target_record:
            if not target_record.is_read:
                target_record.is_read = True
                target_record.save()
        else:
            # 懒创建：用户首次查看该消息
            # 检查用户是否对该类型消息设置了免打扰
            # 系统通知(0)和审核通知(4)不受免打扰影响
            is_muted = False
            if instance.message_type not in [0, 4]:
                is_muted = UserNotificationPreference.objects.filter(
                    user_id=user_id,
                    message_type=instance.message_type,
                    is_muted=True
                ).exists()
            
            MessageCenterTargetUser.objects.create(
                users_id=user_id,
                messagecenter_id=pk,
                is_read=True  # 查看时总是标记为已读
            )

        # 使用详情序列化器返回完整内容
        serializer = MessageCenterDetailSerializer(instance, request=request)

        # 计算未读数：中间表中的未读 + 没有中间表记录的群发消息
        read_msg_ids = set(MessageCenterTargetUser.objects.filter(
            users__id=user_id, is_read=True
        ).values_list('messagecenter_id', flat=True))
        total_visible = self._get_user_visible_queryset(user_id).count()
        total_unread = total_visible - len(read_msg_ids)
        total_unread = max(0, total_unread)

        websocket_push(user_id, message={
            "sender": "system", "contentType": "TEXT",
            "content": "您查看了一条消息~", "unread": total_unread
        })
        return DetailResponse(data=serializer.data, msg="获取成功")

    @action(methods=['GET'], detail=False, permission_classes=[IsAuthenticated])
    def get_self_receive(self, request):
        """获取当前用户接收到的消息

        查询逻辑（动态匹配，不依赖中间表）：
        - target_type=0: 通过中间表关联的指定用户消息
        - target_type=1: 当前用户的角色匹配 target_role
        - target_type=2: 当前用户的部门匹配 target_dept
        - target_type=3: 系统通知，所有用户可见

        支持按 message_type 过滤（可选查询参数）。
        """
        self_user_id = self.request.user.id
        queryset = self._get_user_visible_queryset(self_user_id)

        # 按消息类型过滤（可选，支持逗号分隔的多个值，如 message_type=1,2）
        message_type = request.query_params.get('message_type')
        if message_type is not None and message_type != '':
            try:
                type_list = [int(t.strip()) for t in message_type.split(',') if t.strip()]
                if type_list:
                    queryset = queryset.filter(message_type__in=type_list)
            except (ValueError, TypeError):
                pass

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = MessageCenterTargetUserListSerializer(page, many=True, request=request)
            return self.get_paginated_response(serializer.data)
        serializer = MessageCenterTargetUserListSerializer(queryset, many=True, request=request)
        return SuccessResponse(data=serializer.data, msg="获取成功")

    @action(methods=['GET'], detail=False, permission_classes=[IsAuthenticated])
    def get_newest_msg(self, request):
        """获取当前用户最新的一条消息"""
        self_user_id = self.request.user.id
        queryset = self._get_user_visible_queryset(self_user_id)
        newest = queryset.first()  # 已按 -create_datetime 排序
        data = None
        if newest:
            serializer = MessageCenterTargetUserListSerializer(newest, many=False, request=request)
            data = serializer.data
        return DetailResponse(data=data, msg="获取成功")

    @action(methods=['POST'], detail=False, permission_classes=[IsAuthenticated])
    def mark_all_read(self, request):
        """标记当前用户的所有消息为已读
        
        采用懒创建策略：
        1. 获取用户可见的所有消息
        2. 对于已有中间表记录的，更新 is_read=True
        3. 对于没有中间表记录的，创建记录并标记为已读
        """
        user_id = self.request.user.id
        
        # 获取用户可见的所有消息
        visible_messages = self._get_user_visible_queryset(user_id)
        visible_msg_ids = list(visible_messages.values_list('id', flat=True))
        
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
        
        # 推送 WebSocket 通知
        websocket_push(user_id, message={
            "sender": "system",
            "contentType": "TEXT",
            "content": "所有消息已标记为已读",
            "unread": 0
        })
        
        return DetailResponse(data={"count": len(visible_msg_ids)}, msg="全部已读成功")

    @action(methods=['POST'], detail=False, permission_classes=[IsAuthenticated])
    def mark_type_read(self, request):
        """标记指定类型的消息为已读
        
        用于批量标记某一类型的消息（如点赞通知）为已读。
        
        Request Body:
            message_type (int): 消息类型（0=系统通知, 1=评论, 2=回复, 3=点赞, 4=审核）
            
        Returns:
            Response: 标记成功的消息数量
        """
        user_id = self.request.user.id
        message_type = request.data.get('message_type')
        
        if message_type is None:
            return ErrorResponse(msg="缺少 message_type 参数")
        
        try:
            message_type = int(message_type)
        except (ValueError, TypeError):
            return ErrorResponse(msg="message_type 必须是整数")
        
        # 获取用户可见的指定类型消息
        visible_messages = self._get_user_visible_queryset(user_id).filter(
            message_type=message_type
        )
        visible_msg_ids = list(visible_messages.values_list('id', flat=True))
        
        if not visible_msg_ids:
            return DetailResponse(data={"count": 0}, msg="没有需要标记的消息")
        
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
        
        # 消息类型名称映射
        type_names = {
            0: '系统通知',
            1: '评论',
            2: '回复',
            3: '点赞',
            4: '审核'
        }
        type_name = type_names.get(message_type, '未知类型')
        
        # 推送 WebSocket 通知
        websocket_push(user_id, message={
            "sender": "system",
            "contentType": "TEXT",
            "content": f"所有{type_name}消息已标记为已读",
            "unread": 0
        })
        
        return DetailResponse(
            data={"count": len(visible_msg_ids), "message_type": message_type},
            msg=f"{type_name}消息已全部标记为已读"
        )

    @staticmethod
    def _get_user_visible_queryset(user_id):
        """获取用户可见的所有消息查询集
        
        Args:
            user_id: 用户 ID
            
        Returns:
            QuerySet: 按创建时间倒序排列的消息查询集
        """
        user = Users.objects.get(id=user_id)
        user_role_ids = list(user.role.values_list('id', flat=True))
        user_dept_id = user.dept_id

        q = Q(target_type=3)  # 系统通知
        q |= Q(target_type=0, target_user__id=user_id)  # 指定用户
        if user_role_ids:
            q |= Q(target_type=1, target_role__id__in=user_role_ids)  # 按角色
        if user_dept_id:
            q |= Q(target_type=2, target_dept__id=user_dept_id)  # 按部门

        return MessageCenter.objects.filter(q).distinct().order_by('-create_datetime')

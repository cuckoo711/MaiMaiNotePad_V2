# -*- coding: utf-8 -*-
import urllib

from asgiref.sync import sync_to_async, async_to_sync
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer, AsyncWebsocketConsumer
import json

from channels.layers import get_channel_layer
from jwt import InvalidSignatureError
from rest_framework.request import Request

from application import settings
from mainotebook.system.models import MessageCenter, Users, MessageCenterTargetUser
from mainotebook.system.views.message_center import MessageCenterTargetUserSerializer
from mainotebook.utils.serializers import CustomModelSerializer

send_dict = {}


# 发送消息结构体
def set_message(sender, msg_type, msg, unread=0):
    text = {
        'sender': sender,
        'contentType': msg_type,
        'content': msg,
        'unread': unread
    }
    return text


# 异步获取消息中心的目标用户
@database_sync_to_async
def _get_message_center_instance(message_id):
    from mainotebook.system.models import MessageCenter
    _MessageCenter = MessageCenter.objects.filter(id=message_id).values_list('target_user', flat=True)
    if _MessageCenter:
        return _MessageCenter
    else:
        return []


@database_sync_to_async
def _get_message_unread(user_id):
    """获取用户的未读消息数量"""
    from mainotebook.system.models import MessageCenterTargetUser
    count = MessageCenterTargetUser.objects.filter(users=user_id, is_read=False).count()
    return count or 0


def request_data(scope):
    query_string = scope.get('query_string', b'').decode('utf-8')
    qs = urllib.parse.parse_qs(query_string)
    return qs


class MainotebookWebSocket(AsyncJsonWebsocketConsumer):
    async def connect(self):
        try:
            import jwt
            self.service_uid = self.scope["url_route"]["kwargs"]["service_uid"]
            decoded_result = jwt.decode(self.service_uid, settings.SECRET_KEY, algorithms=["HS256"])
            if decoded_result:
                self.user_id = decoded_result.get('user_id')
                self.chat_group_name = "user_" + str(self.user_id)
                # 收到连接时候处理，
                await self.channel_layer.group_add(
                    self.chat_group_name,
                    self.channel_name
                )
                await self.accept()
                # 主动推送消息
                unread_count = await _get_message_unread(self.user_id)
                if unread_count == 0:
                    # 发送连接成功
                    await self.send_json(set_message('system', 'SYSTEM', '您已上线'))
                else:
                    await self.send_json(
                        set_message('system', 'SYSTEM', "请查看您的未读消息~",
                                    unread=unread_count))
        except InvalidSignatureError:
            await self.disconnect(None)

    async def disconnect(self, close_code):
        # 安全退出房间组（JWT 验证失败时 chat_group_name 可能未初始化）
        if hasattr(self, 'chat_group_name'):
            await self.channel_layer.group_discard(self.chat_group_name, self.channel_name)
        try:
            await self.close(close_code)
        except Exception:
            pass


class MegCenter(MainotebookWebSocket):
    """
    消息中心
    """

    async def receive(self, text_data):
        # 接受客户端的信息，你处理的函数
        text_data_json = json.loads(text_data)
        message_id = text_data_json.get('message_id', None)
        user_list = await _get_message_center_instance(message_id)
        for send_user in user_list:
            await self.channel_layer.group_send(
                "user_" + str(send_user),
                {'type': 'push.message', 'json': text_data_json}
            )

    async def push_message(self, event):
        """消息发送"""
        message = event['json']
        await self.send(text_data=json.dumps(message))


class MessageCreateSerializer(CustomModelSerializer):
    """
    消息中心-新增-序列化器
    """
    class Meta:
        model = MessageCenter
        fields = "__all__"
        read_only_fields = ["id"]


def websocket_push(user_id, message):
    username = "user_" + str(user_id)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        username,
        {
            "type": "push.message",
            "json": message
        }
    )


def create_message_push(title: str, content: str, target_type: int = 0, target_user: list = None, target_dept=None,
                        target_role=None, message: dict = None, request=Request):
    """创建消息并推送给目标用户
    
    投递策略与 MessageCenterCreateSerializer 保持一致：
    - target_type=0: 指定用户，写入中间表
    - target_type=1/2/3: 不写中间表，仅 WebSocket 通知
    
    Args:
        title: 消息标题
        content: 消息内容
        target_type: 目标类型（0=指定用户, 1=按角色, 2=按部门, 3=系统通知/全员）
        target_user: 目标用户 ID 列表（target_type=0 时使用）
        target_dept: 目标部门 ID 列表（target_type=2 时使用）
        target_role: 目标角色 ID 列表（target_type=1 时使用）
        message: WebSocket 推送消息体
        request: 请求对象
    """
    if message is None:
        message = {"contentType": "INFO", "content": None}
    if target_role is None:
        target_role = []
    if target_dept is None:
        target_dept = []
    data = {
        "title": title,
        "content": content,
        "target_type": target_type,
        "target_user": target_user or [],
        "target_dept": target_dept,
        "target_role": target_role
    }
    message_center_instance = MessageCreateSerializer(data=data, request=request)
    message_center_instance.is_valid(raise_exception=True)
    message_center_instance.save()

    ws_message = {**message, "unread": 1}
    channel_layer = get_channel_layer()

    if target_type == 0:
        # 指定用户：写入中间表并逐个推送
        users = target_user or []
        targetuser_data = [
            {"messagecenter": message_center_instance.instance.id, "users": uid}
            for uid in users
        ]
        targetuser_instance = MessageCenterTargetUserSerializer(data=targetuser_data, many=True, request=request)
        targetuser_instance.is_valid(raise_exception=True)
        targetuser_instance.save()
        for uid in users:
            unread_count = async_to_sync(_get_message_unread)(uid)
            async_to_sync(channel_layer.group_send)(
                "user_" + str(uid),
                {"type": "push.message", "json": {**message, "unread": unread_count}}
            )
    elif target_type == 1:
        # 按角色：不写中间表
        user_ids = Users.objects.filter(role__id__in=target_role).values_list('id', flat=True).distinct()
        for uid in user_ids:
            async_to_sync(channel_layer.group_send)(
                "user_" + str(uid), {"type": "push.message", "json": ws_message}
            )
    elif target_type == 2:
        # 按部门：不写中间表
        user_ids = Users.objects.filter(dept__id__in=target_dept).values_list('id', flat=True).distinct()
        for uid in user_ids:
            async_to_sync(channel_layer.group_send)(
                "user_" + str(uid), {"type": "push.message", "json": ws_message}
            )
    elif target_type == 3:
        # 系统通知：不写中间表，广播所有用户
        user_ids = Users.objects.values_list('id', flat=True)
        for uid in user_ids:
            async_to_sync(channel_layer.group_send)(
                "user_" + str(uid), {"type": "push.message", "json": ws_message}
            )
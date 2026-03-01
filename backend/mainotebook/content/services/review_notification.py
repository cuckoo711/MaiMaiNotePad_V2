"""
审核通知服务

封装审核结果通知的创建和推送逻辑。
利用项目已有的 MessageCenter 模型和 websocket_push 函数。
"""

import logging
from typing import Optional
from uuid import UUID

from mainotebook.system.models import MessageCenter, MessageCenterTargetUser
from mainotebook.system.views.message_center import websocket_push

logger = logging.getLogger(__name__)


class ReviewNotificationService:
    """审核通知服务

    封装审核结果通知的创建和 WebSocket 推送逻辑。
    通知失败不影响审核操作本身。
    """

    @staticmethod
    def send_review_notification(
        uploader_id: UUID,
        content_name: str,
        content_type: str,
        action: str,
        reason: Optional[str] = None
    ) -> None:
        """发送审核结果通知

        创建消息中心记录并通过 WebSocket 推送实时消息。
        整个通知逻辑包裹在 try/except 中，失败时仅记录日志不抛出异常。

        Args:
            uploader_id: 内容上传者的用户 ID
            content_name: 内容名称
            content_type: 内容类型（knowledge/persona）
            action: 审核操作（approved/rejected）
            reason: 拒绝原因（仅拒绝时使用）
        """
        try:
            # 根据 action 生成消息标题和内容
            content_type_label = "知识库" if content_type == "knowledge" else "人设卡"

            if action == "approved":
                title = "审核通过通知"
                message_content = f"您的{content_type_label}「{content_name}」已通过审核。"
            else:
                title = "审核拒绝通知"
                message_content = f"您的{content_type_label}「{content_name}」未通过审核。"
                if reason:
                    message_content += f"拒绝原因：{reason}"

            # 创建 MessageCenter 记录（target_type=0 表示指定用户）
            message = MessageCenter.objects.create(
                title=title,
                content=message_content,
                target_type=0,
                message_type=4,
            )

            # 创建目标用户关联记录
            MessageCenterTargetUser.objects.create(
                messagecenter=message,
                users_id=uploader_id
            )

            # 获取未读消息数并通过 WebSocket 推送实时消息
            unread_count = MessageCenterTargetUser.objects.filter(
                users_id=uploader_id, is_read=False
            ).count()
            websocket_push(uploader_id, message={
                "sender": "system",
                "contentType": "SYSTEM",
                "content": "您有一条新消息~",
                "unread": unread_count
            })

        except Exception as e:
            logger.exception(
                "发送审核通知失败: uploader_id=%s, content_name=%s, action=%s",
                uploader_id, content_name, action
            )

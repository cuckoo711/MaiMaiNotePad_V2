"""评论通知服务模块

在评论、回复、点赞等交互行为发生时，向相关用户发送站内信通知并推送 WebSocket 消息。

通知场景：
1. 收到回复：被回复的评论作者收到通知（排除自己回复自己）
2. 收到点赞：被点赞的评论作者收到通知（排除自己点赞自己）
3. 收到评论：知识库/人设卡的作者收到一级评论通知（排除自己评论自己的内容）
"""

import logging
from typing import Optional
from uuid import UUID

from mainotebook.system.models import MessageCenter, MessageCenterTargetUser

logger = logging.getLogger(__name__)


class CommentNotificationService:
    """评论通知服务

    封装评论相关通知的创建和 WebSocket 推送逻辑。
    所有通知方法均包裹在 try/except 中，失败时仅记录日志不抛出异常。
    """

    @staticmethod
    def _send_notification(
        user_id: UUID, title: str, content: str,
        message_type: int = 0, extra_data: dict = None
    ) -> None:
        """发送站内信通知并推送 WebSocket 消息

        Args:
            user_id: 接收通知的用户 ID
            title: 消息标题
            content: 消息内容
            message_type: 消息类型（0=系统通知, 1=评论, 2=回复, 3=点赞, 4=审核）
            extra_data: 扩展数据，如评论 ID、目标内容 ID 等
        """
        from mainotebook.system.views.message_center import websocket_push

        # 创建 MessageCenter 记录（target_type=0 表示指定用户）
        message = MessageCenter.objects.create(
            title=title,
            content=content,
            target_type=0,
            message_type=message_type,
            extra_data=extra_data or {},
        )

        # 创建目标用户关联记录
        MessageCenterTargetUser.objects.create(
            messagecenter=message,
            users_id=user_id
        )

        # 获取未读消息数并通过 WebSocket 推送
        unread_count = MessageCenterTargetUser.objects.filter(
            users_id=user_id, is_read=False
        ).count()
        websocket_push(user_id, message={
            "sender": "system",
            "contentType": "SYSTEM",
            "content": "您有一条新消息~",
            "unread": unread_count
        })

    @staticmethod
    def notify_new_reply(
        comment_author_id: UUID,
        replier_name: str,
        comment_content_preview: str,
        reply_content_preview: str,
        comment_id: str = None,
        reply_id: str = None,
        target_id: str = None,
        target_type: str = None,
        root_comment_id: str = None,
    ) -> None:
        """通知用户收到新回复

        当评论被他人回复时，通知原评论作者。
        自己回复自己的情况应在调用前过滤。

        Args:
            comment_author_id: 被回复评论的作者 ID
            replier_name: 回复者用户名
            comment_content_preview: 原评论内容预览（截取前 30 字）
            reply_content_preview: 回复内容预览（截取前 50 字）
            comment_id: 被回复的评论 ID（用于快捷回复定位）
            reply_id: 新回复的评论 ID
            target_id: 评论所属内容的 ID
            target_type: 评论所属内容的类型（knowledge/persona）
            root_comment_id: 根评论 ID（用于快捷回复时正确挂载到树形结构）
        """
        try:
            title = "收到新回复"
            content = (
                f"{replier_name} 回复了您的评论"
                f"「{comment_content_preview}」：\n"
                f"{reply_content_preview}"
            )
            extra_data = {}
            if comment_id:
                extra_data['comment_id'] = str(comment_id)
            if reply_id:
                extra_data['reply_id'] = str(reply_id)
            if target_id:
                extra_data['target_id'] = str(target_id)
            if target_type:
                extra_data['target_type'] = target_type
            if root_comment_id:
                extra_data['root_comment_id'] = str(root_comment_id)
            CommentNotificationService._send_notification(
                comment_author_id, title, content,
                message_type=2, extra_data=extra_data,
            )
        except Exception:
            logger.exception(
                "发送回复通知失败: comment_author_id=%s", comment_author_id
            )

    @staticmethod
    def notify_new_like(
        comment_author_id: UUID,
        liker_name: str,
        comment_content_preview: str
    ) -> None:
        """通知用户评论被点赞

        当评论被他人点赞时，通知评论作者。
        自己点赞自己的情况应在调用前过滤。

        Args:
            comment_author_id: 被点赞评论的作者 ID
            liker_name: 点赞者用户名
            comment_content_preview: 被点赞评论内容预览（截取前 50 字）
        """
        try:
            title = "收到新点赞"
            content = (
                f"{liker_name} 赞了您的评论"
                f"「{comment_content_preview}」"
            )
            CommentNotificationService._send_notification(
                comment_author_id, title, content, message_type=3,
            )
        except Exception:
            logger.exception(
                "发送点赞通知失败: comment_author_id=%s", comment_author_id
            )

    @staticmethod
    def notify_new_comment_on_content(
        content_owner_id: UUID,
        commenter_name: str,
        content_name: str,
        content_type: str,
        comment_content_preview: str,
        comment_id: str = None,
        target_id: str = None,
    ) -> None:
        """通知内容作者收到新的一级评论

        当自己的知识库或人设卡收到一级评论时，通知内容作者。
        自己评论自己内容的情况应在调用前过滤。

        Args:
            content_owner_id: 内容作者（知识库/人设卡上传者）的用户 ID
            commenter_name: 评论者用户名
            content_name: 内容名称（知识库/人设卡名称）
            content_type: 内容类型（'knowledge' 或 'persona'）
            comment_content_preview: 评论内容预览（截取前 50 字）
            comment_id: 评论 ID（用于快捷回复定位）
            target_id: 评论所属内容的 ID
        """
        try:
            type_label = "知识库" if content_type == "knowledge" else "人设卡"
            title = "收到新评论"
            content = (
                f"{commenter_name} 评论了您的{type_label}"
                f"「{content_name}」：\n"
                f"{comment_content_preview}"
            )
            extra_data = {}
            if comment_id:
                extra_data['comment_id'] = str(comment_id)
            if target_id:
                extra_data['target_id'] = str(target_id)
            if content_type:
                extra_data['target_type'] = content_type
            CommentNotificationService._send_notification(
                content_owner_id, title, content,
                message_type=1, extra_data=extra_data,
            )
        except Exception:
            logger.exception(
                "发送评论通知失败: content_owner_id=%s", content_owner_id
            )

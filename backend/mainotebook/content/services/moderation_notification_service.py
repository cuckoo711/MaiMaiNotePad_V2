# -*- coding: utf-8 -*-
"""禁言封禁通知服务

封装禁言封禁操作的通知创建和推送逻辑。
利用项目已有的 MessageCenter 模型和邮件发送功能。
"""

import logging
from typing import Optional
from datetime import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from mainotebook.system.models import MessageCenter, MessageCenterTargetUser, Users
from mainotebook.system.views.message_center import websocket_push

logger = logging.getLogger(__name__)


class ModerationNotificationService:
    """禁言封禁通知服务
    
    封装禁言封禁操作的通知创建和 WebSocket 推送逻辑。
    通知失败不影响禁言封禁操作本身（降级策略）。
    """
    
    @staticmethod
    def send_mute_notification(user: Users, mute_record) -> None:
        """发送禁言通知
        
        创建消息中心记录并发送 HTML 邮件通知用户被禁言。
        整个通知逻辑包裹在 try/except 中，失败时仅记录日志不抛出异常。
        
        Args:
            user: 被禁言的用户对象
            mute_record: UserMuteRecord 对象，包含禁言详情
        """
        try:
            # 构建通知标题和内容
            title = "禁言通知"
            
            # 格式化禁言时长
            if mute_record.muted_until is None:
                duration_text = "永久"
            else:
                duration_text = f"至 {mute_record.muted_until.strftime('%Y-%m-%d %H:%M:%S')}"
            
            # 禁言类型
            mute_type_text = "AI自动禁言" if mute_record.mute_type == "auto" else "手动禁言"
            
            # 构建消息内容
            message_content = f"""您已被{mute_type_text}。

禁言原因：{mute_record.mute_reason}

禁言时长：{duration_text}

在禁言期间，您将无法发表评论。如有疑问，请联系管理员。"""
            
            # 创建 MessageCenter 记录（target_type=0 表示指定用户）
            message = MessageCenter.objects.create(
                title=title,
                content=message_content,
                target_type=0,
                message_type=4,  # 系统通知
            )
            
            # 创建目标用户关联记录
            MessageCenterTargetUser.objects.create(
                messagecenter=message,
                users_id=user.id
            )
            
            # 获取未读消息数并通过 WebSocket 推送实时消息
            unread_count = MessageCenterTargetUser.objects.filter(
                users_id=user.id, is_read=False
            ).count()
            websocket_push(user.id, message={
                "sender": "system",
                "contentType": "SYSTEM",
                "content": "您有一条新的禁言通知",
                "unread": unread_count
            })
            
            logger.info("消息中心禁言通知已发送: user_id=%s", user.id)
            
            # 发送邮件通知
            try:
                # 渲染 HTML 邮件模板
                html_content = render_to_string(
                    "email/mute_notification.html",
                    {
                        "username": user.username,
                        "mute_reason": mute_record.mute_reason,
                        "duration_text": duration_text,
                        "mute_type": mute_type_text,
                        "muted_until": mute_record.muted_until,
                    },
                )
                
                # 发件人地址
                from_email = f"麦麦 <{settings.DEFAULT_FROM_EMAIL}>"
                
                # 发送邮件
                send_mail(
                    subject="麦麦笔记本 - 禁言通知",
                    message=f"您已被{mute_type_text}。原因：{mute_record.mute_reason}",
                    from_email=from_email,
                    recipient_list=[user.email],
                    html_message=html_content,
                    fail_silently=False,
                )
                
                logger.info("禁言通知邮件已发送: user_id=%s, email=%s", user.id, user.email)
                
            except Exception as email_error:
                # 邮件发送失败不影响主流程（降级策略）
                logger.error(
                    "发送禁言通知邮件失败: user_id=%s, email=%s, error=%s",
                    user.id, user.email, str(email_error)
                )
        
        except Exception as e:
            # 整个通知流程失败也不影响禁言操作本身
            logger.exception(
                "发送禁言通知失败: user_id=%s, mute_record_id=%s",
                user.id, mute_record.id
            )
    
    @staticmethod
    def send_unmute_notification(user: Users, reason: Optional[str] = None) -> None:
        """发送解除禁言通知
        
        创建消息中心记录并发送 HTML 邮件通知用户禁言已解除。
        整个通知逻辑包裹在 try/except 中，失败时仅记录日志不抛出异常。
        
        Args:
            user: 被解除禁言的用户对象
            reason: 解除原因（可选）
        """
        try:
            # 构建通知标题和内容
            title = "解除禁言通知"
            
            # 构建消息内容
            message_content = "您的禁言状态已被解除，现在可以正常发表评论了。"
            
            if reason:
                message_content += f"\n\n解除原因：{reason}"
            
            # 创建 MessageCenter 记录
            message = MessageCenter.objects.create(
                title=title,
                content=message_content,
                target_type=0,
                message_type=4,
            )
            
            # 创建目标用户关联记录
            MessageCenterTargetUser.objects.create(
                messagecenter=message,
                users_id=user.id
            )
            
            # 获取未读消息数并通过 WebSocket 推送实时消息
            unread_count = MessageCenterTargetUser.objects.filter(
                users_id=user.id, is_read=False
            ).count()
            websocket_push(user.id, message={
                "sender": "system",
                "contentType": "SYSTEM",
                "content": "您的禁言已解除",
                "unread": unread_count
            })
            
            logger.info("消息中心解除禁言通知已发送: user_id=%s", user.id)
            
            # 发送邮件通知
            try:
                # 渲染 HTML 邮件模板
                html_content = render_to_string(
                    "email/unmute_notification.html",
                    {
                        "username": user.username,
                        "reason": reason,
                    },
                )
                
                # 发件人地址
                from_email = f"麦麦 <{settings.DEFAULT_FROM_EMAIL}>"
                
                # 发送邮件
                send_mail(
                    subject="麦麦笔记本 - 解除禁言通知",
                    message="您的禁言状态已被解除。",
                    from_email=from_email,
                    recipient_list=[user.email],
                    html_message=html_content,
                    fail_silently=False,
                )
                
                logger.info("解除禁言通知邮件已发送: user_id=%s, email=%s", user.id, user.email)
                
            except Exception as email_error:
                logger.error(
                    "发送解除禁言通知邮件失败: user_id=%s, email=%s, error=%s",
                    user.id, user.email, str(email_error)
                )
        
        except Exception as e:
            logger.exception(
                "发送解除禁言通知失败: user_id=%s",
                user.id
            )
    
    @staticmethod
    def send_ban_notification(user: Users, ban_reason: str, locked_until: Optional[datetime] = None) -> None:
        """发送封禁通知
        
        创建消息中心记录并发送 HTML 邮件通知用户被封禁。
        整个通知逻辑包裹在 try/except 中，失败时仅记录日志不抛出异常。
        
        Args:
            user: 被封禁的用户对象
            ban_reason: 封禁原因
            locked_until: 封禁截止时间（None 表示永久封禁）
        """
        try:
            # 构建通知标题和内容
            title = "封禁通知"
            
            # 格式化封禁时长
            if locked_until is None:
                duration_text = "永久"
            else:
                duration_text = f"至 {locked_until.strftime('%Y-%m-%d %H:%M:%S')}"
            
            # 构建消息内容
            message_content = f"""您的账号已被封禁。

封禁原因：{ban_reason}

封禁时长：{duration_text}

在封禁期间，您将无法登录系统。如有疑问，请联系管理员。"""
            
            # 创建 MessageCenter 记录
            message = MessageCenter.objects.create(
                title=title,
                content=message_content,
                target_type=0,
                message_type=4,
            )
            
            # 创建目标用户关联记录
            MessageCenterTargetUser.objects.create(
                messagecenter=message,
                users_id=user.id
            )
            
            # 获取未读消息数并通过 WebSocket 推送实时消息
            unread_count = MessageCenterTargetUser.objects.filter(
                users_id=user.id, is_read=False
            ).count()
            websocket_push(user.id, message={
                "sender": "system",
                "contentType": "SYSTEM",
                "content": "您有一条新的封禁通知",
                "unread": unread_count
            })
            
            logger.info("消息中心封禁通知已发送: user_id=%s", user.id)
            
            # 发送邮件通知
            try:
                # 渲染 HTML 邮件模板
                html_content = render_to_string(
                    "email/ban_notification.html",
                    {
                        "username": user.username,
                        "ban_reason": ban_reason,
                        "duration_text": duration_text,
                        "locked_until": locked_until,
                    },
                )
                
                # 发件人地址
                from_email = f"麦麦 <{settings.DEFAULT_FROM_EMAIL}>"
                
                # 发送邮件
                send_mail(
                    subject="麦麦笔记本 - 封禁通知",
                    message=f"您的账号已被封禁。原因：{ban_reason}",
                    from_email=from_email,
                    recipient_list=[user.email],
                    html_message=html_content,
                    fail_silently=False,
                )
                
                logger.info("封禁通知邮件已发送: user_id=%s, email=%s", user.id, user.email)
                
            except Exception as email_error:
                logger.error(
                    "发送封禁通知邮件失败: user_id=%s, email=%s, error=%s",
                    user.id, user.email, str(email_error)
                )
        
        except Exception as e:
            logger.exception(
                "发送封禁通知失败: user_id=%s",
                user.id
            )
    
    @staticmethod
    def send_unban_notification(user: Users, reason: Optional[str] = None) -> None:
        """发送解除封禁通知
        
        创建消息中心记录并发送 HTML 邮件通知用户封禁已解除。
        整个通知逻辑包裹在 try/except 中，失败时仅记录日志不抛出异常。
        
        Args:
            user: 被解除封禁的用户对象
            reason: 解除原因（可选）
        """
        try:
            # 构建通知标题和内容
            title = "解除封禁通知"
            
            # 构建消息内容
            message_content = "您的账号封禁状态已被解除，现在可以正常登录系统了。"
            
            if reason:
                message_content += f"\n\n解除原因：{reason}"
            
            # 创建 MessageCenter 记录
            message = MessageCenter.objects.create(
                title=title,
                content=message_content,
                target_type=0,
                message_type=4,
            )
            
            # 创建目标用户关联记录
            MessageCenterTargetUser.objects.create(
                messagecenter=message,
                users_id=user.id
            )
            
            # 获取未读消息数并通过 WebSocket 推送实时消息
            unread_count = MessageCenterTargetUser.objects.filter(
                users_id=user.id, is_read=False
            ).count()
            websocket_push(user.id, message={
                "sender": "system",
                "contentType": "SYSTEM",
                "content": "您的账号封禁已解除",
                "unread": unread_count
            })
            
            logger.info("消息中心解除封禁通知已发送: user_id=%s", user.id)
            
            # 发送邮件通知（复用 unmute_notification.html 模板，因为内容类似）
            try:
                # 渲染 HTML 邮件模板
                html_content = render_to_string(
                    "email/unmute_notification.html",
                    {
                        "username": user.username,
                        "reason": reason,
                        "notification_type": "封禁",  # 用于区分是禁言还是封禁
                    },
                )
                
                # 发件人地址
                from_email = f"麦麦 <{settings.DEFAULT_FROM_EMAIL}>"
                
                # 发送邮件
                send_mail(
                    subject="麦麦笔记本 - 解除封禁通知",
                    message="您的账号封禁状态已被解除。",
                    from_email=from_email,
                    recipient_list=[user.email],
                    html_message=html_content,
                    fail_silently=False,
                )
                
                logger.info("解除封禁通知邮件已发送: user_id=%s, email=%s", user.id, user.email)
                
            except Exception as email_error:
                logger.error(
                    "发送解除封禁通知邮件失败: user_id=%s, email=%s, error=%s",
                    user.id, user.email, str(email_error)
                )
        
        except Exception as e:
            logger.exception(
                "发送解除封禁通知失败: user_id=%s",
                user.id
            )
    
    @staticmethod
    def send_rejection_warning(
        user: Users, 
        current_count: int, 
        threshold: int, 
        rejection_reason: str
    ) -> None:
        """发送评论拒绝警告
        
        创建消息中心记录通知用户评论被拒绝，并提示剩余机会。
        仅发送站内通知，不发送邮件。
        整个通知逻辑包裹在 try/except 中，失败时仅记录日志不抛出异常。
        
        Args:
            user: 用户对象
            current_count: 当前已被拒绝次数
            threshold: 触发自动禁言的阈值
            rejection_reason: 本次拒绝原因
        """
        try:
            # 构建通知标题和内容
            title = "评论审核未通过提醒"
            
            # 计算剩余机会
            remaining_chances = threshold - current_count
            
            # 构建消息内容
            message_content = f"""您的评论未通过审核。

拒绝原因：{rejection_reason}

当前已被拒绝次数：{current_count} 次
距离自动禁言还剩：{remaining_chances} 次机会

温馨提示：在 24 小时内累计 {threshold} 次评论被拒绝，系统将自动禁言 24 小时。请注意遵守社区规范，文明发言。"""
            
            # 创建 MessageCenter 记录（仅站内通知，不发送邮件）
            message = MessageCenter.objects.create(
                title=title,
                content=message_content,
                target_type=0,
                message_type=4,
            )
            
            # 创建目标用户关联记录
            MessageCenterTargetUser.objects.create(
                messagecenter=message,
                users_id=user.id
            )
            
            # 获取未读消息数并通过 WebSocket 推送实时消息
            unread_count = MessageCenterTargetUser.objects.filter(
                users_id=user.id, is_read=False
            ).count()
            websocket_push(user.id, message={
                "sender": "system",
                "contentType": "SYSTEM",
                "content": f"您的评论未通过审核，还剩 {remaining_chances} 次机会",
                "unread": unread_count
            })
            
            logger.info(
                "评论拒绝警告已发送: user_id=%s, current_count=%s, remaining=%s",
                user.id, current_count, remaining_chances
            )
        
        except Exception as e:
            logger.exception(
                "发送评论拒绝警告失败: user_id=%s, current_count=%s",
                user.id, current_count
            )

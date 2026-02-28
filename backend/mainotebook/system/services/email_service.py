# -*- coding: utf-8 -*-
"""邮件服务模块

提供验证邮件的发送功能，包括：
- 渲染 HTML 邮件模板
- 构建验证链接
- 通过 Django SMTP 后端发送邮件
"""

import logging
import smtplib
from typing import Optional, Tuple

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


class EmailService:
    """邮件服务

    负责构建和发送 HTML 格式的验证邮件，
    使用 Django 的邮件后端和模板引擎。
    """

    @staticmethod
    def send_verification_email(
        email: str, username: str, token: str, verification_link_prefix: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """发送验证邮件

        渲染 HTML 模板并通过 SMTP 发送包含验证链接的邮件。
        发件人显示名称为"小麦"。

        Args:
            email: 收件人邮箱地址
            username: 用户名（用于邮件模板中的欢迎语）
            token: 验证令牌
            verification_link_prefix: 验证链接前缀（可选，如果不传则使用默认配置）

        Returns:
            Tuple[bool, Optional[str]]: (是否成功, 失败时的错误信息)
        """
        try:
            # 构建验证链接
            if verification_link_prefix:
                # 去除末尾的斜杠，避免双斜杠
                prefix = verification_link_prefix.rstrip('/')
                verification_url = f"{prefix}?token={token}"
            else:
                # 默认使用 Hash 模式（兼容 admin_web）
                frontend_url = getattr(settings, 'FRONTEND_URL', None)
                if not frontend_url:
                     # 尝试从 conf.env 获取（如果 settings 没加载到）
                     from conf import env
                     frontend_url = getattr(env, 'FRONTEND_URL', 'http://localhost:8080')
                
                verification_url = f"{frontend_url}/#/verify-email?token={token}"

            # 渲染 HTML 邮件模板
            html_content = render_to_string(
                "email/verification.html",
                {
                    "username": username,
                    "verification_url": verification_url,
                },
            )

            # 发件人地址（显示名称为"小麦"）
            from_email = f"麦麦 <{settings.DEFAULT_FROM_EMAIL}>"

            # 发送邮件
            send_mail(
                subject="麦麦笔记本 - 邮箱验证",
                message=f"请点击以下链接完成邮箱验证：{verification_url}",
                from_email=from_email,
                recipient_list=[email],
                html_message=html_content,
                fail_silently=False,
            )

            logger.info("验证邮件已发送至 %s", email)
            return True, None

        except smtplib.SMTPException as e:
            logger.error("SMTP 发送验证邮件失败，收件人: %s，错误: %s", email, str(e))
            return False, "验证邮件发送失败，请稍后重试"

        except Exception as e:
            logger.error("发送验证邮件时发生未知错误，收件人: %s，错误: %s", email, str(e))
            return False, "验证邮件发送失败，请稍后重试"

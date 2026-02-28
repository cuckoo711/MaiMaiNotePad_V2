# -*- coding: utf-8 -*-
"""邮箱验证码服务模块

提供邮箱验证码的生成、存储、校验和发送功能。
验证码存储在 Redis 中，有效期 5 分钟。
"""

import logging
import random
import smtplib
import string
from typing import Optional, Tuple
from uuid import UUID

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django_redis import get_redis_connection

logger = logging.getLogger(__name__)

# Redis key 前缀
EMAIL_CODE_KEY_PREFIX = "email_code:"

# 验证码有效期：5 分钟（秒）
EMAIL_CODE_TTL = 5 * 60

# 验证码长度
CODE_LENGTH = 6


def generate_code(length: int = CODE_LENGTH) -> str:
    """生成纯数字验证码

    Args:
        length: 验证码长度，默认 6 位

    Returns:
        str: 生成的验证码字符串
    """
    return "".join(random.choices(string.digits, k=length))


def store_email_code(user_id: UUID, email: str) -> str:
    """生成并存储邮箱验证码到 Redis

    以 user_id 为维度存储，同一用户重复请求会覆盖旧验证码。

    Args:
        user_id: 用户 UUID
        email: 目标邮箱地址

    Returns:
        str: 生成的验证码
    """
    redis_conn = get_redis_connection("default")
    code = generate_code()
    key = f"{EMAIL_CODE_KEY_PREFIX}{user_id}"

    # 存储验证码和目标邮箱，5 分钟过期
    pipe = redis_conn.pipeline()
    pipe.hset(key, mapping={"code": code, "email": email})
    pipe.expire(key, EMAIL_CODE_TTL)
    pipe.execute()

    logger.info("已为用户 %s 生成邮箱验证码，目标邮箱: %s", user_id, email)
    return code


def verify_email_code(user_id: UUID, email: str, code: str) -> Tuple[bool, Optional[str]]:
    """校验邮箱验证码

    Args:
        user_id: 用户 UUID
        email: 目标邮箱地址
        code: 用户提交的验证码

    Returns:
        Tuple[bool, Optional[str]]: (是否通过, 失败时的错误信息)
    """
    redis_conn = get_redis_connection("default")
    key = f"{EMAIL_CODE_KEY_PREFIX}{user_id}"

    stored_data = redis_conn.hgetall(key)
    if not stored_data:
        return False, "验证码已过期或不存在，请重新获取"

    stored_code = stored_data.get(b"code", b"").decode("utf-8")
    stored_email = stored_data.get(b"email", b"").decode("utf-8")

    if stored_email != email:
        return False, "验证码与目标邮箱不匹配"

    if stored_code != code:
        return False, "验证码错误"

    # 验证通过后删除验证码，防止重复使用
    redis_conn.delete(key)
    logger.info("用户 %s 邮箱验证码校验通过，邮箱: %s", user_id, email)
    return True, None


def send_email_code(email: str, code: str) -> Tuple[bool, Optional[str]]:
    """发送邮箱验证码邮件

    Args:
        email: 收件人邮箱地址
        code: 验证码

    Returns:
        Tuple[bool, Optional[str]]: (是否成功, 失败时的错误信息)
    """
    try:
        html_content = render_to_string(
            "email/email_code.html",
            {"code": code, "ttl_minutes": EMAIL_CODE_TTL // 60},
        )

        from_email = f"麦麦 <{settings.DEFAULT_FROM_EMAIL}>"

        send_mail(
            subject="麦麦笔记本 - 邮箱验证码",
            message=f"您的验证码是：{code}，{EMAIL_CODE_TTL // 60} 分钟内有效。",
            from_email=from_email,
            recipient_list=[email],
            html_message=html_content,
            fail_silently=False,
        )

        logger.info("邮箱验证码已发送至 %s", email)
        return True, None

    except smtplib.SMTPException as e:
        logger.error("SMTP 发送验证码失败，收件人: %s，错误: %s", email, str(e))
        return False, "验证码发送失败，请稍后重试"

    except Exception as e:
        logger.error("发送验证码时发生未知错误，收件人: %s，错误: %s", email, str(e))
        return False, "验证码发送失败，请稍后重试"

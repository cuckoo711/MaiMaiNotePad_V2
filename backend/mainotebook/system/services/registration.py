# -*- coding: utf-8 -*-
"""注册服务模块

提供用户邮箱注册的核心业务逻辑，包括：
- 注册信息暂存到 Redis
- 邮箱验证并创建用户
- 邮箱/用户名唯一性检查
"""

import logging
import secrets
from typing import Dict, Optional, Tuple

from django.contrib.auth.hashers import make_password
from django.db import IntegrityError
from django_redis import get_redis_connection

from application import dispatch
from mainotebook.system.models import Dept, Role, Users

logger = logging.getLogger(__name__)

# Redis key 前缀
PENDING_KEY_PREFIX = "reg:pending:"
TOKEN_KEY_PREFIX = "reg:token:"
USERNAME_KEY_PREFIX = "reg:username:"

# 注册信息过期时间：24 小时（秒）
REGISTRATION_TTL = 24 * 60 * 60


class RegistrationService:
    """注册服务

    处理用户邮箱注册的核心业务逻辑，包括注册信息暂存、
    验证令牌管理、用户创建等功能。
    """

    @staticmethod
    def _get_redis_connection():
        """获取 Redis 连接

        Returns:
            Redis 连接实例
        """
        return get_redis_connection("default")

    @staticmethod
    def check_uniqueness(email: str, username: str) -> Optional[str]:
        """检查邮箱和用户名的唯一性

        同时检查数据库中已有用户和 Redis 中待验证注册的占位锁。

        Args:
            email: 邮箱地址
            username: 用户名

        Returns:
            Optional[str]: 如果存在冲突返回中文错误信息，否则返回 None
        """
        # 检查数据库中邮箱是否已被注册
        if Users.objects.filter(email=email).exists():
            return "该邮箱已被注册"

        # 检查数据库中用户名是否已被注册
        if Users.objects.filter(username=username).exists():
            return "该用户名已被注册"

        # 检查 Redis 中用户名占位锁（其他邮箱的待验证注册）
        redis_conn = RegistrationService._get_redis_connection()
        username_key = f"{USERNAME_KEY_PREFIX}{username}"
        occupied_email = redis_conn.get(username_key)
        if occupied_email:
            occupied_email = occupied_email.decode("utf-8")
            # 如果是同一邮箱的重复注册，不算冲突
            if occupied_email != email:
                return "该用户名已被注册"

        return None

    @staticmethod
    def store_pending_registration(
        email: str, username: str, password: str
    ) -> str:
        """将注册信息暂存到 Redis

        生成验证令牌，将邮箱、用户名、密码哈希存入 Redis，
        同时写入令牌映射和用户名占位锁，TTL 均为 24 小时。
        同一邮箱重复注册时会覆盖旧数据。

        Args:
            email: 邮箱地址
            username: 用户名
            password: 明文密码

        Returns:
            str: 生成的验证令牌
        """
        redis_conn = RegistrationService._get_redis_connection()
        pending_key = f"{PENDING_KEY_PREFIX}{email}"

        # 如果同一邮箱已有待验证注册，先清除旧的 token 和 username 占位
        existing_data = redis_conn.hgetall(pending_key)
        if existing_data:
            old_token = existing_data.get(b"token")
            old_username = existing_data.get(b"username")
            if old_token:
                redis_conn.delete(f"{TOKEN_KEY_PREFIX}{old_token.decode('utf-8')}")
            if old_username:
                redis_conn.delete(f"{USERNAME_KEY_PREFIX}{old_username.decode('utf-8')}")
            logger.info("邮箱 %s 重复注册，已清除旧的待验证数据", email)

        # 生成验证令牌（URL 安全，64+ 字符）
        token = secrets.token_urlsafe(48)

        # 对密码进行哈希处理
        password_hash = make_password(password)

        # 使用 pipeline 原子写入三个 key
        pipe = redis_conn.pipeline()

        # 写入待验证注册信息（Hash）
        pipe.hset(pending_key, mapping={
            "username": username,
            "password_hash": password_hash,
            "token": token,
        })
        pipe.expire(pending_key, REGISTRATION_TTL)

        # 写入令牌 → 邮箱映射（String）
        token_key = f"{TOKEN_KEY_PREFIX}{token}"
        pipe.set(token_key, email, ex=REGISTRATION_TTL)

        # 写入用户名占位锁（String）
        username_key = f"{USERNAME_KEY_PREFIX}{username}"
        pipe.set(username_key, email, ex=REGISTRATION_TTL)

        pipe.execute()

        logger.info("注册信息已暂存到 Redis，邮箱: %s，用户名: %s", email, username)
        return token

    @staticmethod
    def verify_and_create_user(token: str) -> Tuple[bool, Dict]:
        """通过验证令牌创建用户

        从 Redis 读取注册信息，创建数据库用户，分配默认部门和角色，
        原子删除 Redis 中的三个 key，并签发 JWT 令牌。

        Args:
            token: 验证令牌

        Returns:
            Tuple[bool, Dict]: (是否成功, 结果数据)
                成功时返回 (True, {"access": ..., "refresh": ..., ...})
                失败时返回 (False, {"reason": ..., "msg": ...})
        """
        redis_conn = RegistrationService._get_redis_connection()
        token_key = f"{TOKEN_KEY_PREFIX}{token}"

        # 通过 token 查找邮箱
        email = redis_conn.get(token_key)
        if not email:
            logger.warning("验证令牌不存在或已过期: %s...", token[:16])
            return False, {
                "reason": "expired",
                "msg": "验证链接已过期或无效",
            }

        email = email.decode("utf-8")
        pending_key = f"{PENDING_KEY_PREFIX}{email}"

        # 读取待验证注册数据
        pending_data = redis_conn.hgetall(pending_key)
        if not pending_data:
            logger.warning("待验证注册数据不存在，邮箱: %s", email)
            return False, {
                "reason": "expired",
                "msg": "验证链接已过期或无效",
            }

        username = pending_data[b"username"].decode("utf-8")
        password_hash = pending_data[b"password_hash"].decode("utf-8")
        username_key = f"{USERNAME_KEY_PREFIX}{username}"

        # 创建数据库用户
        try:
            user = Users(
                username=username,
                email=email,
                password=password_hash,
                name=username,
                is_active=True,
                user_type=1,  # 前台用户
            )
            user.save()
        except IntegrityError:
            logger.error("创建用户失败（唯一性冲突），邮箱: %s，用户名: %s", email, username)
            return False, {
                "reason": "conflict",
                "msg": "该邮箱或用户名已被注册",
            }

        # 从系统配置分配默认部门和角色
        _assign_default_dept_and_roles(user)

        # 原子删除 Redis 中的三个 key
        pipe = redis_conn.pipeline()
        pipe.delete(token_key)
        pipe.delete(pending_key)
        pipe.delete(username_key)
        pipe.execute()

        # 签发 JWT 令牌
        from mainotebook.system.views.login import LoginSerializer

        refresh = LoginSerializer.get_token(user)
        result = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "username": user.username,
            "name": user.name,
            "userId": user.id,
            "avatar": user.avatar,
            "user_type": user.user_type,
        }

        logger.info("用户注册验证成功，用户 ID: %s，用户名: %s", user.id, user.username)
        return True, result

    @staticmethod
    def resend_verification(email: str) -> Optional[Tuple[str, str]]:
        """重发验证邮件的 token 更新

        从 Redis 读取待验证注册信息，删除旧 token，生成新 token，
        更新 pending hash 中的 token 字段，重置所有 key 的 TTL。

        Args:
            email: 邮箱地址

        Returns:
            Optional[Tuple[str, str]]: (新 token, 用户名) 如果 pending 存在，否则 None
        """
        redis_conn = RegistrationService._get_redis_connection()
        pending_key = f"{PENDING_KEY_PREFIX}{email}"

        # 读取待验证注册数据
        pending_data = redis_conn.hgetall(pending_key)
        if not pending_data:
            return None

        # 删除旧 token key
        old_token = pending_data.get(b"token")
        if old_token:
            redis_conn.delete(f"{TOKEN_KEY_PREFIX}{old_token.decode('utf-8')}")

        # 生成新 token
        new_token = secrets.token_urlsafe(48)
        username = pending_data[b"username"].decode("utf-8")
        username_key = f"{USERNAME_KEY_PREFIX}{username}"

        # 使用 pipeline 原子更新 token 并重置 TTL
        pipe = redis_conn.pipeline()
        pipe.hset(pending_key, "token", new_token)
        pipe.expire(pending_key, REGISTRATION_TTL)
        pipe.set(f"{TOKEN_KEY_PREFIX}{new_token}", email, ex=REGISTRATION_TTL)
        pipe.expire(username_key, REGISTRATION_TTL)
        pipe.execute()

        logger.info("已为邮箱 %s 重新生成验证令牌", email)
        return new_token, username


def _assign_default_dept_and_roles(user: Users) -> None:
    """为新用户分配系统配置中的默认部门和角色

    从系统配置读取 registration.default_dept 和 registration.default_roles，
    如果未配置则兜底使用 key='registered_users' 的部门和 key='user' 的角色。

    Args:
        user: 新创建的用户实例
    """
    # 兜底部门和角色的 key，与 init_dept.json / init_role.json 保持一致
    FALLBACK_DEPT_KEY = "registered_users"
    FALLBACK_ROLE_KEY = "user"

    try:
        system_config = dispatch.get_system_config()

        # 分配默认部门
        default_dept_id = system_config.get("registration.default_dept")
        dept = None
        if default_dept_id:
            try:
                dept = Dept.objects.get(id=default_dept_id)
            except (Dept.DoesNotExist, ValueError, TypeError):
                logger.warning("默认部门配置无效，部门 ID: %s，将使用兜底部门", default_dept_id)

        # 系统配置为空或无效时，按 key 查找兜底部门
        if dept is None:
            dept = Dept.objects.filter(key=FALLBACK_DEPT_KEY).first()
            if dept is None:
                logger.warning("兜底部门 key=%s 不存在，跳过部门分配", FALLBACK_DEPT_KEY)

        if dept:
            user.dept = dept
            user.save(update_fields=["dept"])
            logger.info("已为用户 %s 分配默认部门: %s", user.username, dept.name)

        # 分配默认角色
        default_role_ids = system_config.get("registration.default_roles")
        roles = None
        if default_role_ids:
            # default_role_ids 可能是列表或逗号分隔的字符串
            if isinstance(default_role_ids, str):
                role_id_list = [rid.strip() for rid in default_role_ids.split(",") if rid.strip()]
            elif isinstance(default_role_ids, list):
                role_id_list = default_role_ids
            else:
                role_id_list = []

            if role_id_list:
                try:
                    roles = Role.objects.filter(id__in=role_id_list)
                    if not roles.exists():
                        roles = None
                        logger.warning("默认角色配置无效，角色 IDs: %s，将使用兜底角色", default_role_ids)
                except (ValueError, TypeError):
                    logger.warning("默认角色配置无效，角色 IDs: %s，将使用兜底角色", default_role_ids)

        # 系统配置为空或无效时，按 key 查找兜底角色
        if roles is None:
            fallback_role = Role.objects.filter(key=FALLBACK_ROLE_KEY).first()
            if fallback_role:
                roles = Role.objects.filter(pk=fallback_role.pk)
            else:
                logger.warning("兜底角色 key=%s 不存在，跳过角色分配", FALLBACK_ROLE_KEY)

        if roles is not None and roles.exists():
            user.role.set(roles)
            role_names = ", ".join(r.name for r in roles)
            logger.info("已为用户 %s 分配默认角色: %s", user.username, role_names)

    except Exception as e:
        logger.error("分配默认部门和角色时出错: %s", str(e))

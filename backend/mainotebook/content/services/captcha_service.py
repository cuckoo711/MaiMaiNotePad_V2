"""验证码服务

本模块提供验证码验证和重试限制功能，用于敏感信息确认流程。
集成 django-simple-captcha，实现重试限制（最多 10 次）和冷却期机制（1 分钟）。

**验证需求：9.4, 9.5, 9.6, 9.7**
"""

import logging
from typing import Tuple
from uuid import UUID
from django.core.cache import cache
from captcha.models import CaptchaStore
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CaptchaService:
    """验证码服务
    
    提供验证码验证、重试限制和冷却期管理功能。
    """
    
    # Redis 键前缀
    RETRY_COUNT_PREFIX = "captcha_retry:"
    COOLDOWN_PREFIX = "captcha_cooldown:"
    
    # 配置常量
    MAX_RETRY_COUNT = 10  # 最大重试次数
    COOLDOWN_SECONDS = 60  # 冷却期时长（秒）
    RETRY_COUNT_TTL = 3600  # 重试计数器 TTL（秒）
    
    @staticmethod
    def verify_captcha(captcha_key: str, captcha_value: str) -> bool:
        """验证验证码
        
        验证用户输入的验证码是否正确。
        
        Args:
            captcha_key: 验证码 key（由 django-simple-captcha 生成）
            captcha_value: 用户输入的验证码答案
            
        Returns:
            bool: 验证是否成功
        """
        try:
            # 查询验证码记录
            captcha = CaptchaStore.objects.get(hashkey=captcha_key)
            
            # 检查验证码是否过期
            if captcha.expiration < datetime.now():
                logger.info(f"验证码已过期: key={captcha_key}")
                return False
            
            # 验证答案（不区分大小写）
            is_valid = captcha.response.lower() == captcha_value.lower()
            
            # 验证成功后删除验证码（一次性使用）
            if is_valid:
                captcha.delete()
                logger.info(f"验证码验证成功: key={captcha_key}")
            else:
                logger.info(f"验证码验证失败: key={captcha_key}")
            
            return is_valid
            
        except CaptchaStore.DoesNotExist:
            logger.warning(f"验证码不存在: key={captcha_key}")
            return False
        except Exception as e:
            logger.error(f"验证码验证异常: key={captcha_key}, error={str(e)}")
            return False
    
    @staticmethod
    def check_retry_limit(user_id: UUID) -> Tuple[bool, int]:
        """检查重试次数限制
        
        检查用户是否超过最大重试次数。
        
        Args:
            user_id: 用户 ID
            
        Returns:
            tuple[bool, int]: (是否可以重试, 当前重试次数)
        """
        retry_key = f"{CaptchaService.RETRY_COUNT_PREFIX}{user_id}"
        retry_count = cache.get(retry_key, 0)
        
        can_retry = retry_count < CaptchaService.MAX_RETRY_COUNT
        
        logger.debug(f"检查重试限制: user_id={user_id}, retry_count={retry_count}, can_retry={can_retry}")
        
        return can_retry, retry_count
    
    @staticmethod
    def increment_retry_count(user_id: UUID) -> int:
        """增加重试次数
        
        增加用户的验证码重试次数计数器。
        
        Args:
            user_id: 用户 ID
            
        Returns:
            int: 当前重试次数
        """
        retry_key = f"{CaptchaService.RETRY_COUNT_PREFIX}{user_id}"
        
        # 获取当前计数
        retry_count = cache.get(retry_key, 0)
        retry_count += 1
        
        # 更新计数器，设置 TTL
        cache.set(retry_key, retry_count, CaptchaService.RETRY_COUNT_TTL)
        
        logger.info(f"增加重试次数: user_id={user_id}, retry_count={retry_count}")
        
        # 如果达到最大重试次数，设置冷却期
        if retry_count >= CaptchaService.MAX_RETRY_COUNT:
            CaptchaService.set_cooldown(user_id)
        
        return retry_count
    
    @staticmethod
    def set_cooldown(user_id: UUID) -> None:
        """设置冷却期
        
        设置用户的验证码冷却期，期间不允许验证。
        
        Args:
            user_id: 用户 ID
        """
        cooldown_key = f"{CaptchaService.COOLDOWN_PREFIX}{user_id}"
        
        # 设置冷却期标记，TTL 为冷却期时长
        cache.set(cooldown_key, True, CaptchaService.COOLDOWN_SECONDS)
        
        logger.warning(f"设置冷却期: user_id={user_id}, duration={CaptchaService.COOLDOWN_SECONDS}秒")
    
    @staticmethod
    def check_cooldown(user_id: UUID) -> Tuple[bool, int]:
        """检查是否在冷却期内
        
        检查用户是否处于验证码冷却期。
        
        Args:
            user_id: 用户 ID
            
        Returns:
            tuple[bool, int]: (是否在冷却期内, 剩余冷却时间秒数)
        """
        cooldown_key = f"{CaptchaService.COOLDOWN_PREFIX}{user_id}"
        
        # 检查冷却期标记
        in_cooldown = cache.get(cooldown_key, False)
        
        if in_cooldown:
            # 获取剩余 TTL
            remaining_ttl = cache.ttl(cooldown_key)
            if remaining_ttl is None or remaining_ttl < 0:
                remaining_ttl = 0
            
            logger.debug(f"检查冷却期: user_id={user_id}, in_cooldown=True, remaining={remaining_ttl}秒")
            return True, remaining_ttl
        
        logger.debug(f"检查冷却期: user_id={user_id}, in_cooldown=False")
        return False, 0
    
    @staticmethod
    def reset_retry_count(user_id: UUID) -> None:
        """重置重试次数
        
        重置用户的验证码重试次数计数器（验证成功后调用）。
        
        Args:
            user_id: 用户 ID
        """
        retry_key = f"{CaptchaService.RETRY_COUNT_PREFIX}{user_id}"
        cache.delete(retry_key)
        
        logger.info(f"重置重试次数: user_id={user_id}")
    
    @staticmethod
    def clear_cooldown(user_id: UUID) -> None:
        """清除冷却期
        
        清除用户的验证码冷却期标记（管理员操作或测试用）。
        
        Args:
            user_id: 用户 ID
        """
        cooldown_key = f"{CaptchaService.COOLDOWN_PREFIX}{user_id}"
        cache.delete(cooldown_key)
        
        logger.info(f"清除冷却期: user_id={user_id}")

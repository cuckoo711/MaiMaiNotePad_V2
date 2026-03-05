"""上传限额管理服务

本模块提供用户上传限额管理功能，使用 Redis 缓存管理每日上传次数。
支持每日限额检查（10 次）和 UTC 零点自动重置。

**验证需求：1.3, 1.4**
"""

import logging
from typing import Tuple
from uuid import UUID
from datetime import datetime, timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)


class UploadQuotaService:
    """上传限额管理服务
    
    使用 Redis 管理用户每日上传次数，支持自动重置。
    """
    
    # 配置常量
    DAILY_LIMIT = 10  # 每日上传限额
    REDIS_KEY_PREFIX = "persona_upload_quota:"  # Redis 键前缀
    
    @staticmethod
    def check_quota(user_id: UUID) -> Tuple[bool, int]:
        """检查用户上传限额
        
        检查用户是否还有剩余上传次数。
        
        Args:
            user_id: 用户 ID
            
        Returns:
            tuple[bool, int]: (是否可上传, 剩余次数)
        """
        quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{user_id}"
        
        # 获取当前上传次数
        current_count = cache.get(quota_key, 0)
        
        # 计算剩余次数
        remaining = UploadQuotaService.DAILY_LIMIT - current_count
        can_upload = remaining > 0
        
        logger.debug(
            f"检查上传限额: user_id={user_id}, current={current_count}, "
            f"remaining={remaining}, can_upload={can_upload}"
        )
        
        return can_upload, max(0, remaining)
    
    @staticmethod
    def increment_quota(user_id: UUID) -> int:
        """增加用户上传次数
        
        增加用户的上传次数计数器，并设置 TTL 为到下一个 UTC 零点的秒数。
        
        Args:
            user_id: 用户 ID
            
        Returns:
            int: 当前上传次数
        """
        quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{user_id}"
        
        # 获取当前计数
        current_count = cache.get(quota_key, 0)
        current_count += 1
        
        # 计算到下一个 UTC 零点的秒数
        ttl = UploadQuotaService.get_ttl(user_id)
        
        # 更新计数器，设置 TTL
        cache.set(quota_key, current_count, ttl)
        
        logger.info(
            f"增加上传次数: user_id={user_id}, count={current_count}, ttl={ttl}秒"
        )
        
        return current_count
    
    @staticmethod
    def get_ttl(user_id: UUID) -> int:
        """获取限额重置剩余时间
        
        计算到下一个 UTC 零点的秒数。
        
        Args:
            user_id: 用户 ID
            
        Returns:
            int: 剩余秒数
        """
        # 获取当前 UTC 时间
        now = datetime.now(timezone.utc)
        
        # 计算下一个 UTC 零点
        next_midnight = datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=timezone.utc
        )
        
        # 如果当前时间已经过了今天的零点，计算明天的零点
        if now >= next_midnight:
            from datetime import timedelta
            next_midnight = next_midnight + timedelta(days=1)
        
        # 计算剩余秒数
        remaining_seconds = int((next_midnight - now).total_seconds())
        
        logger.debug(
            f"计算 TTL: user_id={user_id}, now={now}, "
            f"next_midnight={next_midnight}, ttl={remaining_seconds}秒"
        )
        
        return remaining_seconds
    
    @staticmethod
    def get_current_count(user_id: UUID) -> int:
        """获取当前上传次数
        
        获取用户今日已上传的次数。
        
        Args:
            user_id: 用户 ID
            
        Returns:
            int: 当前上传次数
        """
        quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{user_id}"
        current_count = cache.get(quota_key, 0)
        
        logger.debug(f"获取当前上传次数: user_id={user_id}, count={current_count}")
        
        return current_count
    
    @staticmethod
    def reset_quota(user_id: UUID) -> None:
        """重置用户上传限额
        
        重置用户的上传次数计数器（管理员操作或测试用）。
        
        Args:
            user_id: 用户 ID
        """
        quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{user_id}"
        cache.delete(quota_key)
        
        logger.info(f"重置上传限额: user_id={user_id}")

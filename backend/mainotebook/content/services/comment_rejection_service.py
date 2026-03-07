# -*- coding: utf-8 -*-
"""评论拒绝服务

本模块提供评论拒绝记录管理和AI自动禁言触发功能，包括：
- 记录评论被AI审核拒绝的详细信息
- 统计用户在滚动时间窗口内的拒绝次数
- 检查是否达到自动禁言阈值并触发自动禁言
- 发送评论拒绝警告通知

所有操作都使用数据库事务确保原子性。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from django.db import transaction
from django.conf import settings

from mainotebook.content.models import CommentRejectionLog, UserMuteRecord
from mainotebook.system.models import Users
from mainotebook.content.services.moderation_notification_service import ModerationNotificationService

logger = logging.getLogger(__name__)


class CommentRejectionService:
    """评论拒绝服务类
    
    提供评论拒绝记录管理和AI自动禁言触发功能。
    当用户评论被AI审核拒绝时，记录详细信息并检查是否需要触发自动禁言。
    """
    
    @staticmethod
    def get_rejection_count_in_window(user_id: int, hours: int = 24) -> int:
        """统计用户在滚动时间窗口内的拒绝次数
        
        计算从当前时间向前推算指定小时数的时间窗口内，
        该用户被拒绝且计入统计的评论数量。
        
        Args:
            user_id: 用户ID
            hours: 时间窗口大小（小时），默认24小时
            
        Returns:
            int: 拒绝次数
        """
        # 计算窗口起始时间：当前时间 - 指定小时数
        window_start = datetime.now() - timedelta(hours=hours)
        
        # 查询条件：
        # 1. user_id 匹配
        # 2. is_counted=True（计入统计）
        # 3. create_datetime >= 窗口起始时间
        count = CommentRejectionLog.objects.filter(
            user_id=user_id,
            is_counted=True,
            create_datetime__gte=window_start
        ).count()
        
        logger.debug(
            "统计用户拒绝次数: user_id=%s, window_hours=%s, count=%s",
            user_id, hours, count
        )
        
        return count
    
    @staticmethod
    def check_and_trigger_auto_mute(user_id: int) -> bool:
        """检查是否达到自动禁言阈值并触发
        
        从配置读取滚动时间窗口、拒绝次数阈值和自动禁言时长，
        检查用户在窗口内的拒绝次数是否达到阈值。
        如果达到阈值，触发自动禁言流程。
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否触发了自动禁言
        """
        # 从配置读取参数
        window_hours = getattr(settings, 'AUTO_MUTE_WINDOW_HOURS', 24)
        threshold = getattr(settings, 'AUTO_MUTE_THRESHOLD', 6)
        duration_hours = getattr(settings, 'AUTO_MUTE_DURATION_HOURS', 24)
        
        # 统计用户在窗口内的拒绝次数
        rejection_count = CommentRejectionService.get_rejection_count_in_window(
            user_id, window_hours
        )
        
        logger.info(
            "检查自动禁言条件: user_id=%s, rejection_count=%s, threshold=%s",
            user_id, rejection_count, threshold
        )
        
        # 如果次数达到阈值，触发自动禁言
        if rejection_count >= threshold:
            logger.warning(
                "触发自动禁言: user_id=%s, rejection_count=%s, threshold=%s",
                user_id, rejection_count, threshold
            )
            
            # 导入 UserModerationService（延迟导入避免循环依赖）
            from mainotebook.content.services.user_moderation_service import UserModerationService
            
            try:
                # 调用 mute_user 方法执行自动禁言
                # mute_type='auto' 表示AI自动禁言
                # operator_id=None 表示系统自动操作
                UserModerationService.mute_user(
                    user_id=user_id,
                    duration=f"{duration_hours}h",
                    reason=f"在 {window_hours} 小时内累计 {rejection_count} 次评论被拒绝，触发自动禁言",
                    operator_id=None,  # 系统自动操作
                    mute_type='auto'
                )
                
                logger.info(
                    "自动禁言执行成功: user_id=%s, duration=%sh",
                    user_id, duration_hours
                )
                
                return True
                
            except Exception as e:
                logger.exception(
                    "自动禁言执行失败: user_id=%s, error=%s",
                    user_id, str(e)
                )
                # 自动禁言失败不影响评论拒绝记录的创建
                return False
        
        return False
    
    @staticmethod
    def record_rejection(
        user_id: int,
        comment_content: str,
        rejection_reason: str,
        violation_types: list,
        moderation_detail: dict,
        ip_address: str,
        user_agent: str,
        target_type: str,
        target_id: str
    ) -> None:
        """记录评论拒绝并检查是否触发自动禁言
        
        创建 CommentRejectionLog 记录，保存评论被拒绝的详细信息。
        然后检查用户是否达到自动禁言阈值：
        - 如果达到阈值，触发自动禁言
        - 如果未达到阈值，发送警告提示
        
        使用数据库事务确保原子性。
        
        Args:
            user_id: 用户ID
            comment_content: 被拒绝的评论内容
            rejection_reason: 拒绝原因
            violation_types: 违规类型列表
            moderation_detail: AI审核详细信息
            ip_address: 用户IP地址
            user_agent: 用户代理字符串
            target_type: 评论目标类型（如'note'、'comment'）
            target_id: 评论目标ID
        """
        try:
            with transaction.atomic():
                # 创建评论拒绝记录
                rejection_log = CommentRejectionLog.objects.create(
                    user_id=user_id,
                    comment_content=comment_content,
                    rejection_reason=rejection_reason,
                    violation_types=violation_types,
                    moderation_detail=moderation_detail,
                    is_counted=True,  # 默认计入统计
                    ip_address=ip_address,
                    user_agent=user_agent,
                    target_type=target_type,
                    target_id=target_id
                )
                
                logger.info(
                    "评论拒绝记录已创建: rejection_log_id=%s, user_id=%s",
                    rejection_log.id, user_id
                )
                
                # 检查是否触发自动禁言
                triggered = CommentRejectionService.check_and_trigger_auto_mute(user_id)
                
                # 如果未触发自动禁言，发送警告提示
                if not triggered:
                    # 获取配置参数
                    window_hours = getattr(settings, 'AUTO_MUTE_WINDOW_HOURS', 24)
                    threshold = getattr(settings, 'AUTO_MUTE_THRESHOLD', 6)
                    
                    # 获取当前拒绝次数
                    current_count = CommentRejectionService.get_rejection_count_in_window(
                        user_id, window_hours
                    )
                    
                    # 获取用户对象
                    try:
                        user = Users.objects.get(id=user_id)
                        
                        # 发送警告通知
                        ModerationNotificationService.send_rejection_warning(
                            user=user,
                            current_count=current_count,
                            threshold=threshold,
                            rejection_reason=rejection_reason
                        )
                        
                        logger.info(
                            "评论拒绝警告已发送: user_id=%s, current_count=%s, threshold=%s",
                            user_id, current_count, threshold
                        )
                        
                    except Users.DoesNotExist:
                        logger.error(
                            "发送警告失败：用户不存在: user_id=%s",
                            user_id
                        )
                
        except Exception as e:
            logger.exception(
                "记录评论拒绝失败: user_id=%s, error=%s",
                user_id, str(e)
            )
            raise

"""AI 自动审核和用户禁言管理 Celery 异步任务模块

定义 AI 自动审核的异步任务，支持单条和批量审核。
定义用户禁言自动解封任务。
"""

import logging
from typing import Dict

from django.db import transaction
from django.utils import timezone

from application.celery import app

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def auto_review_task(self, content_id: str, content_type: str) -> dict:
    """AI 自动审核异步任务

    调用 AutoReviewService 执行单条内容的 AI 自动审核。
    失败时自动重试，最多 3 次，间隔 60 秒。

    Args:
        self: Celery 任务实例（bind=True）
        content_id: 内容 ID
        content_type: 内容类型（knowledge/persona）

    Returns:
        dict: 审核报告数据

    Raises:
        self.retry: 任务失败时自动重试
    """
    # 延迟导入，避免循环依赖
    from mainotebook.content.services.auto_review_service import AutoReviewService

    try:
        logger.info(
            "开始 AI 自动审核: content_id=%s, content_type=%s",
            content_id, content_type,
        )
        result = AutoReviewService.execute_auto_review(content_id, content_type)
        logger.info(
            "AI 自动审核完成: content_id=%s, content_type=%s",
            content_id, content_type,
        )
        return result
    except Exception as exc:
        logger.error(
            "AI 自动审核失败，准备重试: content_id=%s, content_type=%s, 错误: %s",
            content_id, content_type, exc,
        )
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def batch_auto_review_task(self, content_ids: list, content_type: str) -> dict:
    """批量 AI 自动审核异步任务

    为每条内容分别调用 auto_review_task.delay() 创建独立的异步任务。

    Args:
        self: Celery 任务实例（bind=True）
        content_ids: 内容 ID 列表
        content_type: 内容类型（knowledge/persona）

    Returns:
        dict: 包含 total（总数）和 task_ids（子任务 ID 列表）的字典
    """
    try:
        logger.info(
            "开始批量 AI 自动审核: 数量=%d, content_type=%s",
            len(content_ids), content_type,
        )
        task_ids = []
        for content_id in content_ids:
            result = auto_review_task.delay(str(content_id), content_type)
            task_ids.append(result.id)

        logger.info(
            "批量 AI 自动审核任务已创建: 数量=%d, content_type=%s",
            len(task_ids), content_type,
        )
        return {"total": len(content_ids), "task_ids": task_ids}
    except Exception as exc:
        logger.error(
            "批量 AI 自动审核失败: content_type=%s, 错误: %s",
            content_type, exc,
        )
        raise self.retry(exc=exc)



@app.task(bind=True)
def auto_unmute_task(self, mute_record_id: int) -> Dict[str, any]:
    """自动解封任务
    
    当禁言到期时自动执行解封操作。
    检查 is_manually_modified 标志位，如果为 True 则取消解封。
    任务执行完毕后自动销毁（Celery 默认行为）。
    
    Args:
        self: Celery 任务实例（bind=True）
        mute_record_id: UserMuteRecord 记录 ID
        
    Returns:
        dict: 执行结果，包含 status（success/cancelled/failed）和相关信息
    """
    # 延迟导入，避免循环依赖
    from mainotebook.content.models import UserMuteRecord, Users
    from mainotebook.content.services.moderation_notification_service import (
        ModerationNotificationService,
    )
    
    try:
        # 查询禁言记录
        try:
            mute_record = UserMuteRecord.objects.select_related('user').get(
                id=mute_record_id
            )
        except UserMuteRecord.DoesNotExist:
            error_msg = f"自动解封任务失败：禁言记录不存在，mute_record_id={mute_record_id}"
            logger.error(error_msg)
            return {
                "status": "failed",
                "error": "禁言记录不存在",
                "mute_record_id": mute_record_id,
            }
        
        # 检查 is_manually_modified 标志位
        if mute_record.is_manually_modified:
            # 记录已被人工修改，取消自动解封
            logger.info(
                "自动解封任务取消：记录已被人工修改，user_id=%s, mute_record_id=%s",
                mute_record.user.id,
                mute_record_id,
            )
            return {
                "status": "cancelled",
                "reason": "记录已被人工修改",
                "user_id": mute_record.user.id,
                "mute_record_id": mute_record_id,
            }
        
        # 执行自动解封流程
        with transaction.atomic():
            # 更新 Users 表
            user = mute_record.user
            user.is_muted = False
            user.save(update_fields=['is_muted', 'update_datetime'])
            
            # 更新 UserMuteRecord 表
            mute_record.is_active = False
            mute_record.unmuted_at = timezone.now()
            mute_record.save(update_fields=['is_active', 'unmuted_at', 'update_datetime'])
            
            logger.info(
                "自动解封任务执行成功：user_id=%s, mute_record_id=%s",
                user.id,
                mute_record_id,
            )
        
        # 发送解除禁言通知
        try:
            ModerationNotificationService.send_unmute_notification(
                user=user,
                reason="禁言期限已到，系统自动解除"
            )
        except Exception as notify_error:
            # 通知发送失败不影响主流程，仅记录日志
            logger.warning(
                "自动解封通知发送失败：user_id=%s, error=%s",
                user.id,
                str(notify_error),
            )
        
        return {
            "status": "success",
            "user_id": user.id,
            "username": user.username,
            "mute_record_id": mute_record_id,
            "unmuted_at": mute_record.unmuted_at.isoformat(),
        }
        
    except Exception as exc:
        # 捕获所有异常，记录错误日志
        logger.error(
            "自动解封任务执行失败：mute_record_id=%s, error=%s",
            mute_record_id,
            str(exc),
            exc_info=True,
        )
        return {
            "status": "failed",
            "error": str(exc),
            "mute_record_id": mute_record_id,
        }

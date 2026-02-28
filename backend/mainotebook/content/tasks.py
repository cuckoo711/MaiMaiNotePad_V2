"""AI 自动审核 Celery 异步任务模块

定义 AI 自动审核的异步任务，支持单条和批量审核。
"""

import logging

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

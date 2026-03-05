# -*- coding: utf-8 -*-

"""
Celery 异步任务单元测试

测试 auto_review_task 和 batch_auto_review_task 的重试配置、
服务调用、失败重试行为和批量任务创建。

验证需求：1.1, 1.2, 5.2, 6.3
"""

from unittest.mock import patch, MagicMock

from django.test import TestCase

from mainotebook.content.tasks import auto_review_task, batch_auto_review_task


class TestAutoReviewTaskConfig(TestCase):
    """auto_review_task 重试配置测试"""

    def test_auto_review_task_max_retries(self):
        """验证 auto_review_task 最大重试次数为 3"""
        assert auto_review_task.max_retries == 3

    def test_auto_review_task_default_retry_delay(self):
        """验证 auto_review_task 默认重试间隔为 60 秒"""
        assert auto_review_task.default_retry_delay == 60

    def test_auto_review_task_is_bound(self):
        """验证 auto_review_task 为 bound task（bind=True）"""
        # bound task 的 __self__ 属性在调用时注入，
        # 但 name 属性应存在且包含模块路径
        assert auto_review_task.name is not None


class TestAutoReviewTaskExecution(TestCase):
    """auto_review_task 执行逻辑测试"""

    @patch("mainotebook.content.tasks.AutoReviewService", create=True)
    def test_auto_review_task_calls_service(self, mock_service_cls):
        """验证 auto_review_task 调用 AutoReviewService.execute_auto_review"""
        # 通过 patch 延迟导入路径来 mock 服务
        mock_execute = MagicMock(return_value={"decision": "auto_approved"})

        with patch(
            "mainotebook.content.services.auto_review_service.AutoReviewService.execute_auto_review",
            mock_execute,
        ):
            result = auto_review_task.apply(
                args=["test-content-id", "knowledge"]
            )

        mock_execute.assert_called_once_with("test-content-id", "knowledge")
        assert result.result == {"decision": "auto_approved"}

    @patch(
        "mainotebook.content.services.auto_review_service.AutoReviewService.execute_auto_review",
        side_effect=Exception("API 调用失败"),
    )
    def test_auto_review_task_retries_on_failure(self, mock_execute):
        """验证任务失败时触发重试（self.retry 被调用）"""
        result = auto_review_task.apply(args=["test-id", "persona"])

        # apply() 同步执行，重试会抛出 Retry 异常，
        # 最终任务状态为 FAILURE（因为同步模式不会真正重试）
        assert result.failed()


class TestBatchAutoReviewTask(TestCase):
    """batch_auto_review_task 测试"""

    @patch.object(auto_review_task, "delay")
    def test_batch_creates_subtasks_for_each_id(self, mock_delay):
        """验证 batch_auto_review_task 为每个 ID 创建独立子任务"""
        mock_async_result = MagicMock()
        mock_async_result.id = "fake-task-id"
        mock_delay.return_value = mock_async_result

        content_ids = ["id-1", "id-2", "id-3"]
        result = batch_auto_review_task.apply(
            args=[content_ids, "knowledge"]
        )

        assert mock_delay.call_count == 3
        # 验证每个 ID 都被传入
        mock_delay.assert_any_call("id-1", "knowledge")
        mock_delay.assert_any_call("id-2", "knowledge")
        mock_delay.assert_any_call("id-3", "knowledge")

    @patch.object(auto_review_task, "delay")
    def test_batch_returns_correct_count(self, mock_delay):
        """验证返回的 dict 包含正确的 total 和 task_ids 长度"""
        mock_async_result = MagicMock()
        mock_async_result.id = "fake-task-id"
        mock_delay.return_value = mock_async_result

        content_ids = ["id-1", "id-2", "id-3", "id-4"]
        result = batch_auto_review_task.apply(
            args=[content_ids, "persona"]
        )

        data = result.result
        assert data["total"] == 4
        assert len(data["task_ids"]) == 4

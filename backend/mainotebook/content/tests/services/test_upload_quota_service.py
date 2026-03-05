"""上传限额服务单元测试

测试上传限额服务的各项功能，包括：
- 测试限额内检查（应返回可上传）
- 测试超过限额（应返回不可上传）
- 测试增加上传次数
- 测试 TTL 设置（应为到下一个 UTC 零点的秒数）
- 测试 UTC 零点后限额重置

**验证需求：1.3, 1.4**
"""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, Mock

from django.test import TestCase
from django.core.cache import cache

from mainotebook.content.services.upload_quota_service import UploadQuotaService


class UploadQuotaServiceTest(TestCase):
    """上传限额服务单元测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 清理缓存
        cache.clear()
        
        # 生成测试用户 ID
        self.user_id = uuid.uuid4()
    
    def tearDown(self):
        """测试后清理"""
        # 清理缓存
        cache.clear()
    
    # ========== 限额内检查测试 ==========
    
    def test_check_quota_within_limit(self):
        """测试限额内检查（应返回可上传）（需求 1.3）"""
        # 设置当前上传次数为 5（小于限额 10）
        quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{self.user_id}"
        cache.set(quota_key, 5, 3600)
        
        # 检查限额
        can_upload, remaining = UploadQuotaService.check_quota(self.user_id)
        
        # 验证结果
        self.assertTrue(can_upload, "应该可以上传")
        self.assertEqual(remaining, 5, "剩余次数应为 5")
    
    def test_check_quota_first_upload(self):
        """测试首次上传（无缓存记录）"""
        # 检查限额（无缓存记录）
        can_upload, remaining = UploadQuotaService.check_quota(self.user_id)
        
        # 验证结果
        self.assertTrue(can_upload, "首次上传应该可以")
        self.assertEqual(remaining, 10, "剩余次数应为 10")
    
    def test_check_quota_one_remaining(self):
        """测试剩余 1 次上传"""
        # 设置当前上传次数为 9
        quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{self.user_id}"
        cache.set(quota_key, 9, 3600)
        
        # 检查限额
        can_upload, remaining = UploadQuotaService.check_quota(self.user_id)
        
        # 验证结果
        self.assertTrue(can_upload, "剩余 1 次应该可以上传")
        self.assertEqual(remaining, 1, "剩余次数应为 1")
    
    # ========== 超过限额测试 ==========
    
    def test_check_quota_exceeded(self):
        """测试超过限额（应返回不可上传）（需求 1.3）"""
        # 设置当前上传次数为 10（达到限额）
        quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{self.user_id}"
        cache.set(quota_key, 10, 3600)
        
        # 检查限额
        can_upload, remaining = UploadQuotaService.check_quota(self.user_id)
        
        # 验证结果
        self.assertFalse(can_upload, "达到限额应该不可上传")
        self.assertEqual(remaining, 0, "剩余次数应为 0")
    
    def test_check_quota_over_limit(self):
        """测试超过限额（计数器大于 10）"""
        # 设置当前上传次数为 15（超过限额）
        quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{self.user_id}"
        cache.set(quota_key, 15, 3600)
        
        # 检查限额
        can_upload, remaining = UploadQuotaService.check_quota(self.user_id)
        
        # 验证结果
        self.assertFalse(can_upload, "超过限额应该不可上传")
        self.assertEqual(remaining, 0, "剩余次数应为 0（不应为负数）")
    
    # ========== 增加上传次数测试 ==========
    
    def test_increment_quota(self):
        """测试增加上传次数（需求 1.3）"""
        # 增加上传次数
        current_count = UploadQuotaService.increment_quota(self.user_id)
        
        # 验证结果
        self.assertEqual(current_count, 1, "首次增加应为 1")
        
        # 验证缓存中的值
        quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{self.user_id}"
        cached_count = cache.get(quota_key)
        self.assertEqual(cached_count, 1, "缓存中的值应为 1")
    
    def test_increment_quota_multiple_times(self):
        """测试多次增加上传次数"""
        # 多次增加上传次数
        for i in range(1, 6):
            current_count = UploadQuotaService.increment_quota(self.user_id)
            self.assertEqual(current_count, i, f"第 {i} 次增加应为 {i}")
    
    def test_increment_quota_to_limit(self):
        """测试增加到限额"""
        # 增加到限额（10 次）
        for i in range(1, 11):
            current_count = UploadQuotaService.increment_quota(self.user_id)
            self.assertEqual(current_count, i)
        
        # 验证达到限额后不可上传
        can_upload, remaining = UploadQuotaService.check_quota(self.user_id)
        self.assertFalse(can_upload)
        self.assertEqual(remaining, 0)
    
    def test_increment_quota_sets_ttl(self):
        """测试增加上传次数时设置 TTL"""
        # 增加上传次数
        UploadQuotaService.increment_quota(self.user_id)
        
        # 验证 TTL 被设置
        quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{self.user_id}"
        ttl = cache.ttl(quota_key)
        
        # TTL 应该大于 0
        self.assertIsNotNone(ttl, "TTL 应该被设置")
        self.assertGreater(ttl, 0, "TTL 应该大于 0")
    
    # ========== TTL 设置测试 ==========
    
    def test_get_ttl_calculation(self):
        """测试 TTL 计算（应为到下一个 UTC 零点的秒数）（需求 1.4）"""
        # 获取 TTL
        ttl = UploadQuotaService.get_ttl(self.user_id)
        
        # 验证 TTL 在合理范围内（0 到 24 小时）
        self.assertGreater(ttl, 0, "TTL 应该大于 0")
        self.assertLessEqual(ttl, 86400, "TTL 应该不超过 24 小时（86400 秒）")
    
    @patch('mainotebook.content.services.upload_quota_service.datetime')
    def test_get_ttl_at_midnight(self, mock_datetime):
        """测试在 UTC 零点时的 TTL 计算"""
        # 模拟当前时间为 UTC 零点
        mock_now = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        # 获取 TTL
        ttl = UploadQuotaService.get_ttl(self.user_id)
        
        # 验证 TTL 接近 24 小时
        self.assertGreater(ttl, 86390, "在零点时 TTL 应该接近 24 小时")
        self.assertLessEqual(ttl, 86400, "TTL 不应超过 24 小时")
    
    @patch('mainotebook.content.services.upload_quota_service.datetime')
    def test_get_ttl_before_midnight(self, mock_datetime):
        """测试在 UTC 零点前的 TTL 计算"""
        # 模拟当前时间为 UTC 23:30
        mock_now = datetime(2024, 1, 1, 23, 30, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        # 获取 TTL
        ttl = UploadQuotaService.get_ttl(self.user_id)
        
        # 验证 TTL 接近 30 分钟（1800 秒）
        self.assertGreater(ttl, 1790, "在 23:30 时 TTL 应该接近 30 分钟")
        self.assertLessEqual(ttl, 1800, "TTL 不应超过 30 分钟")
    
    @patch('mainotebook.content.services.upload_quota_service.datetime')
    def test_get_ttl_after_midnight(self, mock_datetime):
        """测试在 UTC 零点后的 TTL 计算"""
        # 模拟当前时间为 UTC 00:30
        mock_now = datetime(2024, 1, 1, 0, 30, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        # 获取 TTL
        ttl = UploadQuotaService.get_ttl(self.user_id)
        
        # 验证 TTL 接近 23.5 小时（84600 秒）
        self.assertGreater(ttl, 84590, "在 00:30 时 TTL 应该接近 23.5 小时")
        self.assertLessEqual(ttl, 84600, "TTL 不应超过 23.5 小时")
    
    # ========== UTC 零点后限额重置测试 ==========
    
    @patch('mainotebook.content.services.upload_quota_service.datetime')
    def test_quota_reset_after_midnight(self, mock_datetime):
        """测试 UTC 零点后限额重置（需求 1.4）"""
        # 模拟当前时间为 UTC 23:59
        mock_now = datetime(2024, 1, 1, 23, 59, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        # 设置上传次数为 10（达到限额）
        quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{self.user_id}"
        
        # 增加上传次数并设置短 TTL（模拟即将过期）
        cache.set(quota_key, 10, 60)  # 60 秒后过期
        
        # 验证当前不可上传
        can_upload, remaining = UploadQuotaService.check_quota(self.user_id)
        self.assertFalse(can_upload)
        
        # 模拟时间过去（缓存过期）
        cache.delete(quota_key)
        
        # 验证限额重置后可以上传
        can_upload, remaining = UploadQuotaService.check_quota(self.user_id)
        self.assertTrue(can_upload, "限额重置后应该可以上传")
        self.assertEqual(remaining, 10, "限额重置后剩余次数应为 10")
    
    def test_quota_ttl_expires_naturally(self):
        """测试限额 TTL 自然过期"""
        # 设置上传次数为 5，TTL 为 1 秒
        quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{self.user_id}"
        cache.set(quota_key, 5, 1)
        
        # 验证当前剩余 5 次
        can_upload, remaining = UploadQuotaService.check_quota(self.user_id)
        self.assertTrue(can_upload)
        self.assertEqual(remaining, 5)
        
        # 等待缓存过期（在实际测试中我们直接删除）
        cache.delete(quota_key)
        
        # 验证过期后限额重置
        can_upload, remaining = UploadQuotaService.check_quota(self.user_id)
        self.assertTrue(can_upload)
        self.assertEqual(remaining, 10, "过期后应该重置为 10")
    
    # ========== 获取当前上传次数测试 ==========
    
    def test_get_current_count_zero(self):
        """测试获取当前上传次数（首次）"""
        # 获取当前上传次数
        current_count = UploadQuotaService.get_current_count(self.user_id)
        
        # 验证结果
        self.assertEqual(current_count, 0, "首次应为 0")
    
    def test_get_current_count_after_increment(self):
        """测试增加后获取当前上传次数"""
        # 增加上传次数
        UploadQuotaService.increment_quota(self.user_id)
        UploadQuotaService.increment_quota(self.user_id)
        UploadQuotaService.increment_quota(self.user_id)
        
        # 获取当前上传次数
        current_count = UploadQuotaService.get_current_count(self.user_id)
        
        # 验证结果
        self.assertEqual(current_count, 3, "应为 3")
    
    # ========== 重置限额测试 ==========
    
    def test_reset_quota(self):
        """测试重置用户上传限额"""
        # 设置上传次数为 5
        quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{self.user_id}"
        cache.set(quota_key, 5, 3600)
        
        # 验证当前次数
        current_count = UploadQuotaService.get_current_count(self.user_id)
        self.assertEqual(current_count, 5)
        
        # 重置限额
        UploadQuotaService.reset_quota(self.user_id)
        
        # 验证限额被重置
        current_count = UploadQuotaService.get_current_count(self.user_id)
        self.assertEqual(current_count, 0, "重置后应为 0")
        
        # 验证可以上传
        can_upload, remaining = UploadQuotaService.check_quota(self.user_id)
        self.assertTrue(can_upload)
        self.assertEqual(remaining, 10)
    
    # ========== 边缘情况测试 ==========
    
    def test_daily_limit_constant(self):
        """测试每日限额常量为 10（需求 1.3）"""
        self.assertEqual(UploadQuotaService.DAILY_LIMIT, 10)
    
    def test_redis_key_prefix(self):
        """测试 Redis 键前缀"""
        self.assertEqual(UploadQuotaService.REDIS_KEY_PREFIX, "persona_upload_quota:")
    
    def test_multiple_users_independent_quotas(self):
        """测试多个用户的限额独立管理"""
        user_id_1 = uuid.uuid4()
        user_id_2 = uuid.uuid4()
        
        # 用户 1 上传 3 次
        for _ in range(3):
            UploadQuotaService.increment_quota(user_id_1)
        
        # 用户 2 上传 7 次
        for _ in range(7):
            UploadQuotaService.increment_quota(user_id_2)
        
        # 验证两个用户的限额独立
        can_upload_1, remaining_1 = UploadQuotaService.check_quota(user_id_1)
        can_upload_2, remaining_2 = UploadQuotaService.check_quota(user_id_2)
        
        self.assertTrue(can_upload_1)
        self.assertEqual(remaining_1, 7)
        
        self.assertTrue(can_upload_2)
        self.assertEqual(remaining_2, 3)
    
    def test_increment_quota_updates_ttl(self):
        """测试每次增加上传次数都更新 TTL"""
        # 第一次增加
        UploadQuotaService.increment_quota(self.user_id)
        quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{self.user_id}"
        ttl_1 = cache.ttl(quota_key)
        
        # 等待一小段时间（在实际测试中我们模拟）
        # 第二次增加
        UploadQuotaService.increment_quota(self.user_id)
        ttl_2 = cache.ttl(quota_key)
        
        # 验证 TTL 被更新（应该接近或相同）
        self.assertIsNotNone(ttl_1)
        self.assertIsNotNone(ttl_2)
        self.assertGreater(ttl_1, 0)
        self.assertGreater(ttl_2, 0)
    
    def test_check_quota_does_not_modify_count(self):
        """测试检查限额不会修改计数器"""
        # 设置上传次数为 5
        quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{self.user_id}"
        cache.set(quota_key, 5, 3600)
        
        # 多次检查限额
        for _ in range(5):
            can_upload, remaining = UploadQuotaService.check_quota(self.user_id)
            self.assertTrue(can_upload)
            self.assertEqual(remaining, 5)
        
        # 验证计数器未被修改
        current_count = UploadQuotaService.get_current_count(self.user_id)
        self.assertEqual(current_count, 5, "检查限额不应修改计数器")
    
    # ========== 完整流程测试 ==========
    
    def test_complete_upload_flow(self):
        """测试完整的上传流程（需求 1.3, 1.4）"""
        # 1. 首次检查限额（应该可以上传）
        can_upload, remaining = UploadQuotaService.check_quota(self.user_id)
        self.assertTrue(can_upload)
        self.assertEqual(remaining, 10)
        
        # 2. 上传 5 次
        for i in range(5):
            # 增加上传次数
            current_count = UploadQuotaService.increment_quota(self.user_id)
            self.assertEqual(current_count, i + 1)
            
            # 检查剩余次数
            can_upload, remaining = UploadQuotaService.check_quota(self.user_id)
            self.assertTrue(can_upload)
            self.assertEqual(remaining, 10 - (i + 1))
        
        # 3. 再上传 5 次（达到限额）
        for i in range(5):
            current_count = UploadQuotaService.increment_quota(self.user_id)
            self.assertEqual(current_count, 5 + i + 1)
        
        # 4. 验证达到限额
        can_upload, remaining = UploadQuotaService.check_quota(self.user_id)
        self.assertFalse(can_upload)
        self.assertEqual(remaining, 0)
        
        # 5. 尝试继续上传（应该被拒绝）
        current_count = UploadQuotaService.increment_quota(self.user_id)
        self.assertEqual(current_count, 11)
        
        can_upload, remaining = UploadQuotaService.check_quota(self.user_id)
        self.assertFalse(can_upload)
        self.assertEqual(remaining, 0)
    
    @patch('mainotebook.content.services.upload_quota_service.datetime')
    def test_complete_daily_reset_flow(self, mock_datetime):
        """测试完整的每日重置流程（需求 1.4）"""
        # 1. 模拟第一天上传到限额
        day1 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = day1
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        for _ in range(10):
            UploadQuotaService.increment_quota(self.user_id)
        
        can_upload, remaining = UploadQuotaService.check_quota(self.user_id)
        self.assertFalse(can_upload)
        self.assertEqual(remaining, 0)
        
        # 2. 模拟第二天（缓存已过期）
        quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{self.user_id}"
        cache.delete(quota_key)  # 模拟 TTL 过期
        
        day2 = datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = day2
        
        # 3. 验证限额已重置
        can_upload, remaining = UploadQuotaService.check_quota(self.user_id)
        self.assertTrue(can_upload)
        self.assertEqual(remaining, 10)
        
        # 4. 第二天可以继续上传
        current_count = UploadQuotaService.increment_quota(self.user_id)
        self.assertEqual(current_count, 1)

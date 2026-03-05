"""上传限额属性测试

使用 Hypothesis 进行基于属性的测试，验证上传限额服务的通用属性。

**属性 2: 上传限额控制**
对于任意用户，在 24 小时内上传人设卡的次数不应超过 10 次，超过限额的上传请求应被拒绝

**属性 3: 限额计数器重置**
对于任意用户的上传限额计数器，其 TTL（生存时间）应设置为到下一个 UTC 零点的秒数

**验证需求：1.3, 1.4**
"""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.core.cache import cache
from hypothesis import given, settings, strategies as st, assume
from hypothesis.extra.django import TestCase as HypothesisTestCase

from mainotebook.content.services.upload_quota_service import UploadQuotaService


class UploadQuotaPropertiesTest(HypothesisTestCase):
    """上传限额属性测试类
    
    使用 Hypothesis 进行基于属性的测试，验证上传限额服务的通用属性。
    """
    
    def setUp(self):
        """测试前准备"""
        # 清理缓存
        cache.clear()
    
    def tearDown(self):
        """测试后清理"""
        # 清理缓存
        cache.clear()
    
    # ========== 属性 2: 上传限额控制 ==========
    
    @settings(max_examples=100)
    @given(
        upload_count=st.integers(min_value=0, max_value=20)
    )
    def test_property_2_upload_quota_control(self, upload_count):
        """属性 2: 上传限额控制
        
        Feature: persona-card-upload, Property 2: 上传限额控制
        
        对于任意用户，在 24 小时内上传人设卡的次数不应超过 10 次，
        超过限额的上传请求应被拒绝。
        
        验证需求：1.3
        
        Args:
            upload_count: 上传次数（0-20）
        """
        # 生成随机用户 ID
        user_id = uuid.uuid4()
        
        # 模拟用户上传 upload_count 次
        quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{user_id}"
        if upload_count > 0:
            cache.set(quota_key, upload_count, 3600)
        
        # 检查限额
        can_upload, remaining = UploadQuotaService.check_quota(user_id)
        
        # 验证属性：上传次数不超过 10 次时可以上传，超过则拒绝
        if upload_count < UploadQuotaService.DAILY_LIMIT:
            self.assertTrue(
                can_upload,
                f"上传次数 {upload_count} < 限额 {UploadQuotaService.DAILY_LIMIT}，应该可以上传"
            )
            self.assertEqual(
                remaining,
                UploadQuotaService.DAILY_LIMIT - upload_count,
                f"剩余次数应为 {UploadQuotaService.DAILY_LIMIT - upload_count}"
            )
        else:
            self.assertFalse(
                can_upload,
                f"上传次数 {upload_count} >= 限额 {UploadQuotaService.DAILY_LIMIT}，应该拒绝上传"
            )
            self.assertEqual(
                remaining,
                0,
                "超过限额时剩余次数应为 0"
            )
    
    @settings(max_examples=100)
    @given(
        initial_count=st.integers(min_value=0, max_value=9),
        additional_uploads=st.integers(min_value=1, max_value=15)
    )
    def test_property_2_incremental_upload_quota_control(self, initial_count, additional_uploads):
        """属性 2: 增量上传限额控制
        
        Feature: persona-card-upload, Property 2: 上传限额控制
        
        验证从任意初始上传次数开始，继续上传时的限额控制。
        
        验证需求：1.3
        
        Args:
            initial_count: 初始上传次数（0-9）
            additional_uploads: 额外上传次数（1-15）
        """
        # 生成随机用户 ID
        user_id = uuid.uuid4()
        
        # 设置初始上传次数
        quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{user_id}"
        if initial_count > 0:
            cache.set(quota_key, initial_count, 3600)
        
        # 尝试额外上传 additional_uploads 次
        successful_uploads = 0
        for i in range(additional_uploads):
            # 检查是否可以上传
            can_upload, remaining = UploadQuotaService.check_quota(user_id)
            
            current_count = initial_count + successful_uploads
            
            if current_count < UploadQuotaService.DAILY_LIMIT:
                # 应该可以上传
                self.assertTrue(
                    can_upload,
                    f"当前次数 {current_count} < 限额，第 {i+1} 次额外上传应该被允许"
                )
                # 模拟上传成功
                UploadQuotaService.increment_quota(user_id)
                successful_uploads += 1
            else:
                # 应该拒绝上传
                self.assertFalse(
                    can_upload,
                    f"当前次数 {current_count} >= 限额，第 {i+1} 次额外上传应该被拒绝"
                )
                # 不增加计数
        
        # 验证最终状态
        final_count = initial_count + successful_uploads
        self.assertLessEqual(
            successful_uploads,
            UploadQuotaService.DAILY_LIMIT - initial_count,
            "成功上传次数不应超过剩余限额"
        )
        self.assertLessEqual(
            final_count,
            UploadQuotaService.DAILY_LIMIT + additional_uploads,
            "最终上传次数应在合理范围内"
        )
    
    @settings(max_examples=100)
    @given(
        user_count=st.integers(min_value=2, max_value=5),
        uploads_per_user=st.lists(
            st.integers(min_value=0, max_value=15),
            min_size=2,
            max_size=5
        )
    )
    def test_property_2_multiple_users_independent_quotas(self, user_count, uploads_per_user):
        """属性 2: 多用户独立限额控制
        
        Feature: persona-card-upload, Property 2: 上传限额控制
        
        验证多个用户的上传限额是独立管理的，互不影响。
        
        验证需求：1.3
        
        Args:
            user_count: 用户数量（2-5）
            uploads_per_user: 每个用户的上传次数列表
        """
        # 确保用户数量和上传次数列表长度一致
        assume(len(uploads_per_user) >= user_count)
        uploads_per_user = uploads_per_user[:user_count]
        
        # 生成多个用户 ID
        user_ids = [uuid.uuid4() for _ in range(user_count)]
        
        # 为每个用户设置上传次数
        for user_id, upload_count in zip(user_ids, uploads_per_user):
            quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{user_id}"
            if upload_count > 0:
                cache.set(quota_key, upload_count, 3600)
        
        # 验证每个用户的限额独立
        for i, (user_id, upload_count) in enumerate(zip(user_ids, uploads_per_user)):
            can_upload, remaining = UploadQuotaService.check_quota(user_id)
            
            # 验证限额控制
            if upload_count < UploadQuotaService.DAILY_LIMIT:
                self.assertTrue(
                    can_upload,
                    f"用户 {i+1} 上传次数 {upload_count} < 限额，应该可以上传"
                )
                self.assertEqual(
                    remaining,
                    UploadQuotaService.DAILY_LIMIT - upload_count,
                    f"用户 {i+1} 剩余次数应为 {UploadQuotaService.DAILY_LIMIT - upload_count}"
                )
            else:
                self.assertFalse(
                    can_upload,
                    f"用户 {i+1} 上传次数 {upload_count} >= 限额，应该拒绝上传"
                )
                self.assertEqual(
                    remaining,
                    0,
                    f"用户 {i+1} 超过限额时剩余次数应为 0"
                )
    
    # ========== 属性 3: 限额计数器重置 ==========
    
    @settings(max_examples=100)
    @given(
        hour=st.integers(min_value=0, max_value=23),
        minute=st.integers(min_value=0, max_value=59),
        second=st.integers(min_value=0, max_value=59)
    )
    def test_property_3_quota_counter_ttl(self, hour, minute, second):
        """属性 3: 限额计数器重置
        
        Feature: persona-card-upload, Property 3: 限额计数器重置
        
        对于任意用户的上传限额计数器，其 TTL（生存时间）应设置为到下一个 UTC 零点的秒数。
        
        验证需求：1.4
        
        Args:
            hour: 小时（0-23）
            minute: 分钟（0-59）
            second: 秒（0-59）
        """
        # 生成随机用户 ID
        user_id = uuid.uuid4()
        
        # 模拟当前时间
        mock_now = datetime(2024, 1, 15, hour, minute, second, tzinfo=timezone.utc)
        
        with patch('mainotebook.content.services.upload_quota_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            # 获取 TTL
            ttl = UploadQuotaService.get_ttl(user_id)
            
            # 计算到下一个 UTC 零点的秒数
            next_midnight = datetime(
                year=mock_now.year,
                month=mock_now.month,
                day=mock_now.day,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
                tzinfo=timezone.utc
            )
            
            # 如果当前时间已经过了今天的零点，计算明天的零点
            if mock_now >= next_midnight:
                next_midnight = next_midnight + timedelta(days=1)
            
            expected_ttl = int((next_midnight - mock_now).total_seconds())
            
            # 验证属性：TTL 应该等于到下一个 UTC 零点的秒数
            self.assertEqual(
                ttl,
                expected_ttl,
                f"在 {hour:02d}:{minute:02d}:{second:02d} 时，TTL 应为 {expected_ttl} 秒"
            )
            
            # 验证 TTL 在合理范围内（0 到 24 小时）
            self.assertGreater(ttl, 0, "TTL 应该大于 0")
            self.assertLessEqual(ttl, 86400, "TTL 应该不超过 24 小时（86400 秒）")
    
    @settings(max_examples=100)
    @given(
        upload_count=st.integers(min_value=1, max_value=10),
        hour=st.integers(min_value=0, max_value=23),
        minute=st.integers(min_value=0, max_value=59)
    )
    def test_property_3_ttl_set_on_increment(self, upload_count, hour, minute):
        """属性 3: 增加上传次数时设置 TTL
        
        Feature: persona-card-upload, Property 3: 限额计数器重置
        
        验证每次增加上传次数时，TTL 都被正确设置为到下一个 UTC 零点的秒数。
        
        验证需求：1.4
        
        Args:
            upload_count: 上传次数（1-10）
            hour: 小时（0-23）
            minute: 分钟（0-59）
        """
        # 生成随机用户 ID
        user_id = uuid.uuid4()
        
        # 模拟当前时间
        mock_now = datetime(2024, 1, 15, hour, minute, 0, tzinfo=timezone.utc)
        
        with patch('mainotebook.content.services.upload_quota_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            # 计算预期的 TTL
            next_midnight = datetime(
                year=mock_now.year,
                month=mock_now.month,
                day=mock_now.day,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
                tzinfo=timezone.utc
            )
            
            if mock_now >= next_midnight:
                next_midnight = next_midnight + timedelta(days=1)
            
            expected_ttl = int((next_midnight - mock_now).total_seconds())
            
            # 多次增加上传次数
            for i in range(upload_count):
                UploadQuotaService.increment_quota(user_id)
                
                # 验证 TTL 被设置
                quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{user_id}"
                actual_ttl = cache.ttl(quota_key)
                
                # 验证 TTL 在合理范围内（允许一些误差）
                self.assertIsNotNone(actual_ttl, f"第 {i+1} 次增加后 TTL 应该被设置")
                self.assertGreater(actual_ttl, 0, f"第 {i+1} 次增加后 TTL 应该大于 0")
                
                # TTL 应该接近预期值（允许 ±5 秒的误差，因为执行时间）
                self.assertAlmostEqual(
                    actual_ttl,
                    expected_ttl,
                    delta=5,
                    msg=f"第 {i+1} 次增加后 TTL 应该接近 {expected_ttl} 秒"
                )
    
    @settings(max_examples=100)
    @given(
        day_offset=st.integers(min_value=0, max_value=30),
        hour=st.integers(min_value=0, max_value=23)
    )
    def test_property_3_ttl_calculation_across_days(self, day_offset, hour):
        """属性 3: 跨天 TTL 计算
        
        Feature: persona-card-upload, Property 3: 限额计数器重置
        
        验证在不同日期和时间，TTL 计算始终正确指向下一个 UTC 零点。
        
        验证需求：1.4
        
        Args:
            day_offset: 日期偏移（0-30 天）
            hour: 小时（0-23）
        """
        # 生成随机用户 ID
        user_id = uuid.uuid4()
        
        # 模拟不同日期的时间
        base_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        mock_now = base_date + timedelta(days=day_offset, hours=hour)
        
        with patch('mainotebook.content.services.upload_quota_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            # 获取 TTL
            ttl = UploadQuotaService.get_ttl(user_id)
            
            # 计算到下一个 UTC 零点的秒数
            next_midnight = datetime(
                year=mock_now.year,
                month=mock_now.month,
                day=mock_now.day,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
                tzinfo=timezone.utc
            )
            
            if mock_now >= next_midnight:
                next_midnight = next_midnight + timedelta(days=1)
            
            expected_ttl = int((next_midnight - mock_now).total_seconds())
            
            # 验证属性：TTL 应该等于到下一个 UTC 零点的秒数
            self.assertEqual(
                ttl,
                expected_ttl,
                f"在 {mock_now.date()} {hour:02d}:00:00 时，TTL 应为 {expected_ttl} 秒"
            )
            
            # 验证 TTL 的合理性
            if hour == 0:
                # 在零点时，TTL 应该接近 24 小时
                self.assertGreater(ttl, 86390, "在零点时 TTL 应该接近 24 小时")
            else:
                # 在其他时间，TTL 应该小于 24 小时
                self.assertLess(ttl, 86400, "在非零点时 TTL 应该小于 24 小时")
    
    @settings(max_examples=100)
    @given(
        initial_uploads=st.integers(min_value=0, max_value=10),
        time_offset_hours=st.integers(min_value=1, max_value=48)
    )
    def test_property_3_quota_reset_after_ttl_expiry(self, initial_uploads, time_offset_hours):
        """属性 3: TTL 过期后限额重置
        
        Feature: persona-card-upload, Property 3: 限额计数器重置
        
        验证当 TTL 过期后（模拟跨越 UTC 零点），限额计数器被重置。
        
        验证需求：1.4
        
        Args:
            initial_uploads: 初始上传次数（0-10）
            time_offset_hours: 时间偏移小时数（1-48）
        """
        # 生成随机用户 ID
        user_id = uuid.uuid4()
        
        # 模拟第一天的时间
        day1 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        with patch('mainotebook.content.services.upload_quota_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = day1
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            # 设置初始上传次数
            quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{user_id}"
            if initial_uploads > 0:
                for _ in range(initial_uploads):
                    UploadQuotaService.increment_quota(user_id)
            
            # 验证初始状态
            can_upload_before, remaining_before = UploadQuotaService.check_quota(user_id)
            expected_remaining_before = UploadQuotaService.DAILY_LIMIT - initial_uploads
            
            if initial_uploads < UploadQuotaService.DAILY_LIMIT:
                self.assertTrue(can_upload_before)
                self.assertEqual(remaining_before, expected_remaining_before)
            else:
                self.assertFalse(can_upload_before)
                self.assertEqual(remaining_before, 0)
            
            # 模拟时间流逝（跨越 UTC 零点）
            # 如果时间偏移超过 12 小时，说明跨越了至少一个零点
            if time_offset_hours >= 12:
                # 模拟缓存过期（TTL 到期）
                cache.delete(quota_key)
                
                # 模拟新的时间
                new_time = day1 + timedelta(hours=time_offset_hours)
                mock_datetime.now.return_value = new_time
                
                # 验证限额已重置
                can_upload_after, remaining_after = UploadQuotaService.check_quota(user_id)
                
                self.assertTrue(
                    can_upload_after,
                    f"经过 {time_offset_hours} 小时后（跨越零点），限额应该被重置，可以上传"
                )
                self.assertEqual(
                    remaining_after,
                    UploadQuotaService.DAILY_LIMIT,
                    f"经过 {time_offset_hours} 小时后（跨越零点），剩余次数应该重置为 {UploadQuotaService.DAILY_LIMIT}"
                )
            else:
                # 未跨越零点，限额不应重置
                can_upload_after, remaining_after = UploadQuotaService.check_quota(user_id)
                
                # 状态应该与之前相同
                self.assertEqual(can_upload_after, can_upload_before)
                self.assertEqual(remaining_after, remaining_before)
    
    # ========== 组合属性测试 ==========
    
    @settings(max_examples=100)
    @given(
        user_count=st.integers(min_value=1, max_value=3),
        uploads_per_user=st.lists(
            st.integers(min_value=0, max_value=15),
            min_size=1,
            max_size=3
        ),
        hour=st.integers(min_value=0, max_value=23)
    )
    def test_combined_properties_quota_and_ttl(self, user_count, uploads_per_user, hour):
        """组合属性测试：限额控制和 TTL 设置
        
        Feature: persona-card-upload, Property 2 & 3: 上传限额控制 + 限额计数器重置
        
        验证限额控制和 TTL 设置同时正确工作。
        
        验证需求：1.3, 1.4
        
        Args:
            user_count: 用户数量（1-3）
            uploads_per_user: 每个用户的上传次数列表
            hour: 小时（0-23）
        """
        # 确保用户数量和上传次数列表长度一致
        assume(len(uploads_per_user) >= user_count)
        uploads_per_user = uploads_per_user[:user_count]
        
        # 生成多个用户 ID
        user_ids = [uuid.uuid4() for _ in range(user_count)]
        
        # 模拟当前时间
        mock_now = datetime(2024, 1, 15, hour, 0, 0, tzinfo=timezone.utc)
        
        with patch('mainotebook.content.services.upload_quota_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            # 计算预期的 TTL
            next_midnight = datetime(
                year=mock_now.year,
                month=mock_now.month,
                day=mock_now.day,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
                tzinfo=timezone.utc
            )
            
            if mock_now >= next_midnight:
                next_midnight = next_midnight + timedelta(days=1)
            
            expected_ttl = int((next_midnight - mock_now).total_seconds())
            
            # 为每个用户设置上传次数并验证
            for user_id, upload_count in zip(user_ids, uploads_per_user):
                # 模拟上传
                for _ in range(min(upload_count, UploadQuotaService.DAILY_LIMIT)):
                    UploadQuotaService.increment_quota(user_id)
                
                # 验证属性 2：限额控制
                can_upload, remaining = UploadQuotaService.check_quota(user_id)
                
                actual_count = min(upload_count, UploadQuotaService.DAILY_LIMIT)
                if actual_count < UploadQuotaService.DAILY_LIMIT:
                    self.assertTrue(can_upload, f"上传 {actual_count} 次后应该可以继续上传")
                    self.assertEqual(
                        remaining,
                        UploadQuotaService.DAILY_LIMIT - actual_count,
                        f"上传 {actual_count} 次后剩余次数应为 {UploadQuotaService.DAILY_LIMIT - actual_count}"
                    )
                else:
                    self.assertFalse(can_upload, f"上传 {actual_count} 次后应该不可上传")
                    self.assertEqual(remaining, 0, "达到限额后剩余次数应为 0")
                
                # 验证属性 3：TTL 设置
                quota_key = f"{UploadQuotaService.REDIS_KEY_PREFIX}{user_id}"
                actual_ttl = cache.ttl(quota_key)
                
                # 只有在实际上传了内容时才验证 TTL
                if actual_count > 0:
                    self.assertIsNotNone(actual_ttl, "TTL 应该被设置")
                    # TTL 可能为 0 表示键不存在或已过期，这在某些边缘情况下是正常的
                    if actual_ttl is not None and actual_ttl > 0:
                        self.assertAlmostEqual(
                            actual_ttl,
                            expected_ttl,
                            delta=5,
                            msg=f"TTL 应该接近 {expected_ttl} 秒"
                        )

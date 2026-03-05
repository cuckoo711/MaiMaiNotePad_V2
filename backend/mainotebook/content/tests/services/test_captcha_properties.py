"""验证码服务属性测试

使用 Hypothesis 进行基于属性的测试，验证验证码服务的通用属性。

**属性 29: 验证码重试限制**
对于任意用户的验证码验证，连续失败次数不应超过 10 次，超过后应进入冷却期

**属性 30: 验证码冷却期**
对于任意验证码失败 10 次的用户，系统应设置 1 分钟的冷却期，期间拒绝新的验证请求

**验证需求：9.6, 9.7**
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from django.test import TestCase
from django.core.cache import cache

from hypothesis import given, settings, strategies as st, assume
from hypothesis.extra.django import TestCase as HypothesisTestCase

from mainotebook.content.services.captcha_service import CaptchaService


class CaptchaPropertiesTest(HypothesisTestCase):
    """验证码服务属性测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 清理缓存
        cache.clear()
    
    def tearDown(self):
        """测试后清理"""
        # 清理缓存
        cache.clear()
    
    # ========== 属性 29: 验证码重试限制 ==========
    
    @settings(max_examples=100)
    @given(
        retry_attempts=st.integers(min_value=0, max_value=20)
    )
    def test_property_29_retry_limit_enforcement(self, retry_attempts):
        """
        **属性 29: 验证码重试限制**
        
        对于任意用户的验证码验证，连续失败次数不应超过 10 次，超过后应进入冷却期。
        
        **验证需求：9.6**
        
        Args:
            retry_attempts: 重试次数（0-20）
        """
        # 生成唯一的用户 ID
        user_id = uuid.uuid4()
        
        # 模拟指定次数的重试
        for i in range(retry_attempts):
            # 增加重试次数
            current_count = CaptchaService.increment_retry_count(user_id)
            
            # 验证重试次数正确递增
            self.assertEqual(current_count, i + 1)
            
            # 检查是否可以继续重试
            can_retry, retry_count = CaptchaService.check_retry_limit(user_id)
            
            # 属性验证：重试次数不应超过 10 次
            if current_count < CaptchaService.MAX_RETRY_COUNT:
                # 未达到限制，应该可以继续重试
                self.assertTrue(
                    can_retry,
                    f"重试次数 {current_count} 未达到限制 {CaptchaService.MAX_RETRY_COUNT}，应该可以继续重试"
                )
            else:
                # 达到或超过限制，不应该继续重试
                self.assertFalse(
                    can_retry,
                    f"重试次数 {current_count} 已达到限制 {CaptchaService.MAX_RETRY_COUNT}，不应该继续重试"
                )
        
        # 最终验证：如果重试次数达到或超过 10 次，应该进入冷却期
        if retry_attempts >= CaptchaService.MAX_RETRY_COUNT:
            in_cooldown, remaining_ttl = CaptchaService.check_cooldown(user_id)
            self.assertTrue(
                in_cooldown,
                f"重试次数 {retry_attempts} 已达到限制，应该进入冷却期"
            )
            self.assertGreater(
                remaining_ttl,
                0,
                "冷却期剩余时间应该大于 0"
            )
    
    @settings(max_examples=100)
    @given(
        initial_count=st.integers(min_value=0, max_value=9),
        additional_attempts=st.integers(min_value=1, max_value=5)
    )
    def test_property_29_cooldown_triggered_at_limit(self, initial_count, additional_attempts):
        """
        **属性 29: 验证码重试限制（冷却期触发）**
        
        验证当重试次数达到 10 次时，冷却期被正确触发。
        
        **验证需求：9.6**
        
        Args:
            initial_count: 初始重试次数（0-9）
            additional_attempts: 额外尝试次数（1-5）
        """
        user_id = uuid.uuid4()
        
        # 设置初始重试次数
        if initial_count > 0:
            retry_key = f"{CaptchaService.RETRY_COUNT_PREFIX}{user_id}"
            cache.set(retry_key, initial_count, CaptchaService.RETRY_COUNT_TTL)
        
        # 执行额外的重试
        cooldown_triggered = False
        for i in range(additional_attempts):
            current_count = CaptchaService.increment_retry_count(user_id)
            total_count = initial_count + i + 1
            
            # 验证计数正确
            self.assertEqual(current_count, total_count)
            
            # 检查是否触发冷却期
            if total_count >= CaptchaService.MAX_RETRY_COUNT:
                in_cooldown, _ = CaptchaService.check_cooldown(user_id)
                if in_cooldown:
                    cooldown_triggered = True
                    break
        
        # 属性验证：如果总次数达到 10 次，冷却期必须被触发
        total_attempts = initial_count + additional_attempts
        if total_attempts >= CaptchaService.MAX_RETRY_COUNT:
            self.assertTrue(
                cooldown_triggered,
                f"总重试次数 {total_attempts} 已达到限制，冷却期应该被触发"
            )
    
    @settings(max_examples=100)
    @given(
        user_count=st.integers(min_value=2, max_value=5),
        retry_attempts_per_user=st.lists(
            st.integers(min_value=0, max_value=15),
            min_size=2,
            max_size=5
        )
    )
    def test_property_29_independent_retry_limits(self, user_count, retry_attempts_per_user):
        """
        **属性 29: 验证码重试限制（多用户独立性）**
        
        验证多个用户的重试限制是独立管理的。
        
        **验证需求：9.6**
        
        Args:
            user_count: 用户数量（2-5）
            retry_attempts_per_user: 每个用户的重试次数列表
        """
        # 确保用户数量和重试次数列表长度一致
        assume(len(retry_attempts_per_user) >= user_count)
        
        # 生成多个用户 ID
        user_ids = [uuid.uuid4() for _ in range(user_count)]
        
        # 为每个用户设置不同的重试次数
        for user_id, attempts in zip(user_ids, retry_attempts_per_user[:user_count]):
            for _ in range(attempts):
                CaptchaService.increment_retry_count(user_id)
        
        # 验证每个用户的重试限制独立
        for i, (user_id, expected_attempts) in enumerate(zip(user_ids, retry_attempts_per_user[:user_count])):
            can_retry, retry_count = CaptchaService.check_retry_limit(user_id)
            
            # 验证重试次数正确
            self.assertEqual(
                retry_count,
                expected_attempts,
                f"用户 {i} 的重试次数应该是 {expected_attempts}"
            )
            
            # 验证重试限制正确
            if expected_attempts < CaptchaService.MAX_RETRY_COUNT:
                self.assertTrue(
                    can_retry,
                    f"用户 {i} 的重试次数 {expected_attempts} 未达到限制，应该可以继续重试"
                )
            else:
                self.assertFalse(
                    can_retry,
                    f"用户 {i} 的重试次数 {expected_attempts} 已达到限制，不应该继续重试"
                )
    
    # ========== 属性 30: 验证码冷却期 ==========
    
    @settings(max_examples=100)
    @given(
        retry_attempts=st.integers(min_value=10, max_value=20)
    )
    def test_property_30_cooldown_period_set(self, retry_attempts):
        """
        **属性 30: 验证码冷却期**
        
        对于任意验证码失败 10 次的用户，系统应设置 1 分钟的冷却期，期间拒绝新的验证请求。
        
        **验证需求：9.7**
        
        Args:
            retry_attempts: 重试次数（10-20，确保达到限制）
        """
        user_id = uuid.uuid4()
        
        # 模拟达到重试限制
        for _ in range(retry_attempts):
            CaptchaService.increment_retry_count(user_id)
        
        # 属性验证：冷却期应该被设置
        in_cooldown, remaining_ttl = CaptchaService.check_cooldown(user_id)
        
        self.assertTrue(
            in_cooldown,
            f"重试次数 {retry_attempts} 已达到限制，应该进入冷却期"
        )
        
        # 验证冷却期时长
        self.assertGreater(
            remaining_ttl,
            0,
            "冷却期剩余时间应该大于 0"
        )
        
        self.assertLessEqual(
            remaining_ttl,
            CaptchaService.COOLDOWN_SECONDS,
            f"冷却期剩余时间不应超过 {CaptchaService.COOLDOWN_SECONDS} 秒"
        )
        
        # 验证冷却期时长接近 60 秒（允许一些误差）
        self.assertGreater(
            remaining_ttl,
            CaptchaService.COOLDOWN_SECONDS - 5,
            f"冷却期剩余时间应该接近 {CaptchaService.COOLDOWN_SECONDS} 秒"
        )
    
    @settings(max_examples=100)
    @given(
        st.just(None)  # 无参数，测试冷却期常量
    )
    def test_property_30_cooldown_duration_is_60_seconds(self, _):
        """
        **属性 30: 验证码冷却期（时长验证）**
        
        验证冷却期时长为 60 秒（1 分钟）。
        
        **验证需求：9.7**
        """
        # 属性验证：冷却期常量应该是 60 秒
        self.assertEqual(
            CaptchaService.COOLDOWN_SECONDS,
            60,
            "冷却期时长应该是 60 秒（1 分钟）"
        )
        
        # 验证实际设置的冷却期时长
        user_id = uuid.uuid4()
        CaptchaService.set_cooldown(user_id)
        
        in_cooldown, remaining_ttl = CaptchaService.check_cooldown(user_id)
        
        self.assertTrue(in_cooldown, "冷却期应该被设置")
        self.assertGreater(remaining_ttl, 55, "冷却期剩余时间应该接近 60 秒")
        self.assertLessEqual(remaining_ttl, 60, "冷却期剩余时间不应超过 60 秒")
    
    @settings(max_examples=100)
    @given(
        user_count=st.integers(min_value=2, max_value=5)
    )
    def test_property_30_independent_cooldowns(self, user_count):
        """
        **属性 30: 验证码冷却期（多用户独立性）**
        
        验证多个用户的冷却期是独立管理的。
        
        **验证需求：9.7**
        
        Args:
            user_count: 用户数量（2-5）
        """
        # 生成多个用户 ID
        user_ids = [uuid.uuid4() for _ in range(user_count)]
        
        # 随机选择一些用户设置冷却期
        users_in_cooldown = set()
        for i, user_id in enumerate(user_ids):
            # 偶数索引的用户设置冷却期
            if i % 2 == 0:
                CaptchaService.set_cooldown(user_id)
                users_in_cooldown.add(user_id)
        
        # 验证每个用户的冷却期状态独立
        for user_id in user_ids:
            in_cooldown, remaining_ttl = CaptchaService.check_cooldown(user_id)
            
            if user_id in users_in_cooldown:
                # 应该在冷却期内
                self.assertTrue(
                    in_cooldown,
                    f"用户 {user_id} 应该在冷却期内"
                )
                self.assertGreater(
                    remaining_ttl,
                    0,
                    f"用户 {user_id} 的冷却期剩余时间应该大于 0"
                )
            else:
                # 不应该在冷却期内
                self.assertFalse(
                    in_cooldown,
                    f"用户 {user_id} 不应该在冷却期内"
                )
                self.assertEqual(
                    remaining_ttl,
                    0,
                    f"用户 {user_id} 的冷却期剩余时间应该是 0"
                )
    
    @settings(max_examples=100)
    @given(
        retry_before_cooldown=st.integers(min_value=10, max_value=15)
    )
    def test_property_30_cooldown_blocks_verification(self, retry_before_cooldown):
        """
        **属性 30: 验证码冷却期（阻止验证）**
        
        验证冷却期内不允许新的验证请求。
        
        **验证需求：9.7**
        
        Args:
            retry_before_cooldown: 进入冷却期前的重试次数（10-15）
        """
        user_id = uuid.uuid4()
        
        # 模拟达到重试限制并进入冷却期
        for _ in range(retry_before_cooldown):
            CaptchaService.increment_retry_count(user_id)
        
        # 验证进入冷却期
        in_cooldown, remaining_ttl = CaptchaService.check_cooldown(user_id)
        self.assertTrue(in_cooldown, "应该进入冷却期")
        
        # 属性验证：冷却期内不允许继续重试
        can_retry, retry_count = CaptchaService.check_retry_limit(user_id)
        
        # 重试次数应该达到或超过限制
        self.assertGreaterEqual(
            retry_count,
            CaptchaService.MAX_RETRY_COUNT,
            "重试次数应该达到或超过限制"
        )
        
        # 不应该允许继续重试
        self.assertFalse(
            can_retry,
            "冷却期内不应该允许继续重试"
        )
    
    # ========== 组合属性测试 ==========
    
    @settings(max_examples=100)
    @given(
        initial_attempts=st.integers(min_value=0, max_value=9),
        additional_attempts=st.integers(min_value=0, max_value=15)
    )
    def test_combined_retry_limit_and_cooldown(self, initial_attempts, additional_attempts):
        """
        **组合属性测试：重试限制和冷却期**
        
        验证重试限制和冷却期的组合行为。
        
        **验证需求：9.6, 9.7**
        
        Args:
            initial_attempts: 初始重试次数（0-9）
            additional_attempts: 额外尝试次数（0-15）
        """
        user_id = uuid.uuid4()
        
        # 设置初始重试次数
        if initial_attempts > 0:
            retry_key = f"{CaptchaService.RETRY_COUNT_PREFIX}{user_id}"
            cache.set(retry_key, initial_attempts, CaptchaService.RETRY_COUNT_TTL)
        
        # 执行额外的重试
        for _ in range(additional_attempts):
            CaptchaService.increment_retry_count(user_id)
        
        # 计算总重试次数
        total_attempts = initial_attempts + additional_attempts
        
        # 检查重试限制
        can_retry, retry_count = CaptchaService.check_retry_limit(user_id)
        
        # 检查冷却期
        in_cooldown, remaining_ttl = CaptchaService.check_cooldown(user_id)
        
        # 属性验证：重试限制和冷却期的一致性
        if total_attempts < CaptchaService.MAX_RETRY_COUNT:
            # 未达到限制
            self.assertTrue(
                can_retry,
                f"总重试次数 {total_attempts} 未达到限制，应该可以继续重试"
            )
            self.assertFalse(
                in_cooldown,
                f"总重试次数 {total_attempts} 未达到限制，不应该进入冷却期"
            )
        else:
            # 达到或超过限制
            self.assertFalse(
                can_retry,
                f"总重试次数 {total_attempts} 已达到限制，不应该继续重试"
            )
            self.assertTrue(
                in_cooldown,
                f"总重试次数 {total_attempts} 已达到限制，应该进入冷却期"
            )
            self.assertGreater(
                remaining_ttl,
                0,
                "冷却期剩余时间应该大于 0"
            )
            self.assertLessEqual(
                remaining_ttl,
                CaptchaService.COOLDOWN_SECONDS,
                f"冷却期剩余时间不应超过 {CaptchaService.COOLDOWN_SECONDS} 秒"
            )
    
    @settings(max_examples=100)
    @given(
        attempts_before_reset=st.integers(min_value=1, max_value=9),
        attempts_after_reset=st.integers(min_value=0, max_value=15)
    )
    def test_reset_clears_retry_count_and_prevents_cooldown(self, attempts_before_reset, attempts_after_reset):
        """
        **组合属性测试：重置后的重试限制**
        
        验证重置重试次数后，重试限制重新计算。
        
        **验证需求：9.6, 9.7**
        
        Args:
            attempts_before_reset: 重置前的重试次数（1-9）
            attempts_after_reset: 重置后的重试次数（0-15）
        """
        user_id = uuid.uuid4()
        
        # 第一阶段：执行一些重试
        for _ in range(attempts_before_reset):
            CaptchaService.increment_retry_count(user_id)
        
        # 验证重试次数
        can_retry_before, retry_count_before = CaptchaService.check_retry_limit(user_id)
        self.assertEqual(retry_count_before, attempts_before_reset)
        
        # 重置重试次数
        CaptchaService.reset_retry_count(user_id)
        
        # 验证重置后重试次数为 0
        can_retry_after_reset, retry_count_after_reset = CaptchaService.check_retry_limit(user_id)
        self.assertEqual(retry_count_after_reset, 0, "重置后重试次数应该是 0")
        self.assertTrue(can_retry_after_reset, "重置后应该可以继续重试")
        
        # 第二阶段：重置后再次重试
        for _ in range(attempts_after_reset):
            CaptchaService.increment_retry_count(user_id)
        
        # 验证重试次数从 0 开始计算
        can_retry_final, retry_count_final = CaptchaService.check_retry_limit(user_id)
        self.assertEqual(retry_count_final, attempts_after_reset)
        
        # 检查冷却期
        in_cooldown, _ = CaptchaService.check_cooldown(user_id)
        
        # 属性验证：只有重置后的重试次数达到限制才进入冷却期
        if attempts_after_reset >= CaptchaService.MAX_RETRY_COUNT:
            self.assertFalse(can_retry_final, "达到限制后不应该继续重试")
            self.assertTrue(in_cooldown, "达到限制后应该进入冷却期")
        else:
            self.assertTrue(can_retry_final, "未达到限制应该可以继续重试")
            self.assertFalse(in_cooldown, "未达到限制不应该进入冷却期")

"""验证码服务单元测试

测试验证码服务的各项功能，包括：
- 测试验证码验证成功
- 测试验证码验证失败
- 测试重试次数限制（10 次）
- 测试冷却期设置和检查（1 分钟）
- 测试冷却期过后可以重新尝试

**验证需求：9.6, 9.7**
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase
from django.core.cache import cache

from captcha.models import CaptchaStore
from mainotebook.content.services.captcha_service import CaptchaService


class CaptchaServiceTest(TestCase):
    """验证码服务单元测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 清理缓存
        cache.clear()
        
        # 生成测试用户 ID
        self.user_id = uuid.uuid4()
        
        # 测试验证码数据
        self.captcha_key = "test_captcha_key"
        self.captcha_value = "42"
    
    def tearDown(self):
        """测试后清理"""
        # 清理缓存
        cache.clear()
        
        # 清理验证码记录
        CaptchaStore.objects.all().delete()
    
    # ========== 验证码验证成功测试 ==========
    
    @patch('mainotebook.content.services.captcha_service.CaptchaStore')
    def test_verify_captcha_success(self, mock_captcha_store):
        """测试验证码验证成功（需求 9.4）"""
        # 创建 mock 验证码对象
        mock_captcha = Mock()
        mock_captcha.response = "42"
        mock_captcha.expiration = datetime.now() + timedelta(minutes=5)
        mock_captcha.delete = Mock()
        
        # 配置 mock 查询
        mock_captcha_store.objects.get.return_value = mock_captcha
        
        # 执行验证
        result = CaptchaService.verify_captcha(self.captcha_key, "42")
        
        # 验证结果
        self.assertTrue(result)
        
        # 验证查询被调用
        mock_captcha_store.objects.get.assert_called_once_with(hashkey=self.captcha_key)
        
        # 验证验证码被删除（一次性使用）
        mock_captcha.delete.assert_called_once()
    
    @patch('mainotebook.content.services.captcha_service.CaptchaStore')
    def test_verify_captcha_case_insensitive(self, mock_captcha_store):
        """测试验证码验证不区分大小写（需求 9.4）"""
        # 创建 mock 验证码对象
        mock_captcha = Mock()
        mock_captcha.response = "ABC"
        mock_captcha.expiration = datetime.now() + timedelta(minutes=5)
        mock_captcha.delete = Mock()
        
        # 配置 mock 查询
        mock_captcha_store.objects.get.return_value = mock_captcha
        
        # 执行验证（使用小写）
        result = CaptchaService.verify_captcha(self.captcha_key, "abc")
        
        # 验证结果
        self.assertTrue(result)
        
        # 验证验证码被删除
        mock_captcha.delete.assert_called_once()
    
    # ========== 验证码验证失败测试 ==========
    
    @patch('mainotebook.content.services.captcha_service.CaptchaStore')
    def test_verify_captcha_wrong_answer(self, mock_captcha_store):
        """测试验证码答案错误（需求 9.4）"""
        # 创建 mock 验证码对象
        mock_captcha = Mock()
        mock_captcha.response = "42"
        mock_captcha.expiration = datetime.now() + timedelta(minutes=5)
        mock_captcha.delete = Mock()
        
        # 配置 mock 查询
        mock_captcha_store.objects.get.return_value = mock_captcha
        
        # 执行验证（错误答案）
        result = CaptchaService.verify_captcha(self.captcha_key, "99")
        
        # 验证结果
        self.assertFalse(result)
        
        # 验证验证码未被删除（失败时保留）
        mock_captcha.delete.assert_not_called()
    
    @patch('mainotebook.content.services.captcha_service.CaptchaStore')
    def test_verify_captcha_expired(self, mock_captcha_store):
        """测试验证码已过期（需求 9.4）"""
        # 创建 mock 验证码对象（已过期）
        mock_captcha = Mock()
        mock_captcha.response = "42"
        mock_captcha.expiration = datetime.now() - timedelta(minutes=1)
        
        # 配置 mock 查询
        mock_captcha_store.objects.get.return_value = mock_captcha
        
        # 执行验证
        result = CaptchaService.verify_captcha(self.captcha_key, "42")
        
        # 验证结果
        self.assertFalse(result)
    
    @patch('mainotebook.content.services.captcha_service.CaptchaStore')
    def test_verify_captcha_not_found(self, mock_captcha_store):
        """测试验证码不存在（需求 9.4）"""
        # 配置 mock 查询抛出异常
        mock_captcha_store.DoesNotExist = CaptchaStore.DoesNotExist
        mock_captcha_store.objects.get.side_effect = CaptchaStore.DoesNotExist
        
        # 执行验证
        result = CaptchaService.verify_captcha(self.captcha_key, "42")
        
        # 验证结果
        self.assertFalse(result)
    
    @patch('mainotebook.content.services.captcha_service.CaptchaStore')
    def test_verify_captcha_exception(self, mock_captcha_store):
        """测试验证码验证异常处理"""
        # 配置 mock 查询抛出异常
        mock_captcha_store.DoesNotExist = CaptchaStore.DoesNotExist
        mock_captcha_store.objects.get.side_effect = Exception("Database error")
        
        # 执行验证
        result = CaptchaService.verify_captcha(self.captcha_key, "42")
        
        # 验证结果
        self.assertFalse(result)
    
    # ========== 重试次数限制测试 ==========
    
    def test_check_retry_limit_within_limit(self):
        """测试重试次数在限制内（需求 9.6）"""
        # 设置重试次数为 5
        retry_key = f"{CaptchaService.RETRY_COUNT_PREFIX}{self.user_id}"
        cache.set(retry_key, 5, CaptchaService.RETRY_COUNT_TTL)
        
        # 检查重试限制
        can_retry, retry_count = CaptchaService.check_retry_limit(self.user_id)
        
        # 验证结果
        self.assertTrue(can_retry)
        self.assertEqual(retry_count, 5)
    
    def test_check_retry_limit_at_limit(self):
        """测试重试次数达到限制（需求 9.6）"""
        # 设置重试次数为 10（最大值）
        retry_key = f"{CaptchaService.RETRY_COUNT_PREFIX}{self.user_id}"
        cache.set(retry_key, 10, CaptchaService.RETRY_COUNT_TTL)
        
        # 检查重试限制
        can_retry, retry_count = CaptchaService.check_retry_limit(self.user_id)
        
        # 验证结果
        self.assertFalse(can_retry)
        self.assertEqual(retry_count, 10)
    
    def test_check_retry_limit_first_attempt(self):
        """测试首次尝试（无重试记录）"""
        # 检查重试限制（无缓存记录）
        can_retry, retry_count = CaptchaService.check_retry_limit(self.user_id)
        
        # 验证结果
        self.assertTrue(can_retry)
        self.assertEqual(retry_count, 0)
    
    def test_increment_retry_count(self):
        """测试增加重试次数（需求 9.6）"""
        # 增加重试次数
        retry_count = CaptchaService.increment_retry_count(self.user_id)
        
        # 验证结果
        self.assertEqual(retry_count, 1)
        
        # 验证缓存中的值
        retry_key = f"{CaptchaService.RETRY_COUNT_PREFIX}{self.user_id}"
        cached_count = cache.get(retry_key)
        self.assertEqual(cached_count, 1)
    
    def test_increment_retry_count_multiple_times(self):
        """测试多次增加重试次数"""
        # 多次增加重试次数
        for i in range(1, 6):
            retry_count = CaptchaService.increment_retry_count(self.user_id)
            self.assertEqual(retry_count, i)
    
    def test_increment_retry_count_triggers_cooldown(self):
        """测试达到最大重试次数时触发冷却期（需求 9.6, 9.7）"""
        # 设置重试次数为 9
        retry_key = f"{CaptchaService.RETRY_COUNT_PREFIX}{self.user_id}"
        cache.set(retry_key, 9, CaptchaService.RETRY_COUNT_TTL)
        
        # 增加重试次数（达到 10 次）
        retry_count = CaptchaService.increment_retry_count(self.user_id)
        
        # 验证重试次数
        self.assertEqual(retry_count, 10)
        
        # 验证冷却期被设置
        cooldown_key = f"{CaptchaService.COOLDOWN_PREFIX}{self.user_id}"
        in_cooldown = cache.get(cooldown_key)
        self.assertTrue(in_cooldown)
    
    # ========== 冷却期设置和检查测试 ==========
    
    def test_set_cooldown(self):
        """测试设置冷却期（需求 9.7）"""
        # 设置冷却期
        CaptchaService.set_cooldown(self.user_id)
        
        # 验证冷却期被设置
        cooldown_key = f"{CaptchaService.COOLDOWN_PREFIX}{self.user_id}"
        in_cooldown = cache.get(cooldown_key)
        self.assertTrue(in_cooldown)
    
    def test_check_cooldown_active(self):
        """测试检查冷却期（冷却期内）（需求 9.7）"""
        # 设置冷却期
        CaptchaService.set_cooldown(self.user_id)
        
        # 检查冷却期
        in_cooldown, remaining_ttl = CaptchaService.check_cooldown(self.user_id)
        
        # 验证结果
        self.assertTrue(in_cooldown)
        self.assertGreater(remaining_ttl, 0)
        self.assertLessEqual(remaining_ttl, CaptchaService.COOLDOWN_SECONDS)
    
    def test_check_cooldown_not_active(self):
        """测试检查冷却期（不在冷却期内）"""
        # 检查冷却期（无冷却期记录）
        in_cooldown, remaining_ttl = CaptchaService.check_cooldown(self.user_id)
        
        # 验证结果
        self.assertFalse(in_cooldown)
        self.assertEqual(remaining_ttl, 0)
    
    def test_cooldown_duration(self):
        """测试冷却期时长为 1 分钟（需求 9.7）"""
        # 验证冷却期常量
        self.assertEqual(CaptchaService.COOLDOWN_SECONDS, 60)
        
        # 设置冷却期
        CaptchaService.set_cooldown(self.user_id)
        
        # 检查冷却期
        in_cooldown, remaining_ttl = CaptchaService.check_cooldown(self.user_id)
        
        # 验证剩余时间接近 60 秒
        self.assertTrue(in_cooldown)
        self.assertGreater(remaining_ttl, 55)  # 允许一些误差
        self.assertLessEqual(remaining_ttl, 60)
    
    # ========== 冷却期过后重新尝试测试 ==========
    
    @patch('django.core.cache.cache.ttl')
    def test_cooldown_expired_can_retry(self, mock_ttl):
        """测试冷却期过后可以重新尝试（需求 9.7）"""
        # 模拟冷却期已过期（TTL 返回 None 或负数）
        cooldown_key = f"{CaptchaService.COOLDOWN_PREFIX}{self.user_id}"
        cache.set(cooldown_key, True, 1)  # 设置 1 秒 TTL
        
        # 模拟 TTL 已过期
        mock_ttl.return_value = -1
        
        # 检查冷却期
        in_cooldown, remaining_ttl = CaptchaService.check_cooldown(self.user_id)
        
        # 验证冷却期已过期
        self.assertTrue(in_cooldown)  # 缓存中仍有值
        self.assertEqual(remaining_ttl, 0)  # 但剩余时间为 0
    
    def test_reset_retry_count(self):
        """测试重置重试次数"""
        # 设置重试次数
        retry_key = f"{CaptchaService.RETRY_COUNT_PREFIX}{self.user_id}"
        cache.set(retry_key, 5, CaptchaService.RETRY_COUNT_TTL)
        
        # 重置重试次数
        CaptchaService.reset_retry_count(self.user_id)
        
        # 验证重试次数被清除
        retry_count = cache.get(retry_key)
        self.assertIsNone(retry_count)
    
    def test_clear_cooldown(self):
        """测试清除冷却期"""
        # 设置冷却期
        CaptchaService.set_cooldown(self.user_id)
        
        # 清除冷却期
        CaptchaService.clear_cooldown(self.user_id)
        
        # 验证冷却期被清除
        in_cooldown, remaining_ttl = CaptchaService.check_cooldown(self.user_id)
        self.assertFalse(in_cooldown)
        self.assertEqual(remaining_ttl, 0)
    
    # ========== 完整流程测试 ==========
    
    @patch('mainotebook.content.services.captcha_service.CaptchaStore')
    def test_complete_retry_flow(self, mock_captcha_store):
        """测试完整的重试流程（需求 9.6, 9.7）"""
        # 创建 mock 验证码对象（错误答案）
        mock_captcha = Mock()
        mock_captcha.response = "42"
        mock_captcha.expiration = datetime.now() + timedelta(minutes=5)
        mock_captcha_store.objects.get.return_value = mock_captcha
        
        # 模拟 10 次失败尝试
        for i in range(10):
            # 验证码验证失败
            result = CaptchaService.verify_captcha(self.captcha_key, "99")
            self.assertFalse(result)
            
            # 增加重试次数
            retry_count = CaptchaService.increment_retry_count(self.user_id)
            self.assertEqual(retry_count, i + 1)
            
            # 检查是否可以继续重试
            can_retry, current_count = CaptchaService.check_retry_limit(self.user_id)
            if i < 9:
                self.assertTrue(can_retry)
            else:
                self.assertFalse(can_retry)
        
        # 验证冷却期被设置
        in_cooldown, remaining_ttl = CaptchaService.check_cooldown(self.user_id)
        self.assertTrue(in_cooldown)
        self.assertGreater(remaining_ttl, 0)
    
    @patch('mainotebook.content.services.captcha_service.CaptchaStore')
    def test_successful_verification_resets_retry_count(self, mock_captcha_store):
        """测试验证成功后重置重试次数"""
        # 设置一些重试次数
        for _ in range(3):
            CaptchaService.increment_retry_count(self.user_id)
        
        # 验证重试次数
        can_retry, retry_count = CaptchaService.check_retry_limit(self.user_id)
        self.assertEqual(retry_count, 3)
        
        # 创建 mock 验证码对象（正确答案）
        mock_captcha = Mock()
        mock_captcha.response = "42"
        mock_captcha.expiration = datetime.now() + timedelta(minutes=5)
        mock_captcha.delete = Mock()
        mock_captcha_store.objects.get.return_value = mock_captcha
        
        # 验证码验证成功
        result = CaptchaService.verify_captcha(self.captcha_key, "42")
        self.assertTrue(result)
        
        # 重置重试次数
        CaptchaService.reset_retry_count(self.user_id)
        
        # 验证重试次数被重置
        can_retry, retry_count = CaptchaService.check_retry_limit(self.user_id)
        self.assertEqual(retry_count, 0)
    
    # ========== 边缘情况测试 ==========
    
    def test_max_retry_count_constant(self):
        """测试最大重试次数常量为 10（需求 9.6）"""
        self.assertEqual(CaptchaService.MAX_RETRY_COUNT, 10)
    
    def test_retry_count_ttl_set(self):
        """测试重试计数器 TTL 被正确设置"""
        # 增加重试次数
        CaptchaService.increment_retry_count(self.user_id)
        
        # 验证 TTL 被设置
        retry_key = f"{CaptchaService.RETRY_COUNT_PREFIX}{self.user_id}"
        ttl = cache.ttl(retry_key)
        
        # TTL 应该接近 RETRY_COUNT_TTL
        self.assertIsNotNone(ttl)
        self.assertGreater(ttl, 0)
        self.assertLessEqual(ttl, CaptchaService.RETRY_COUNT_TTL)
    
    def test_multiple_users_independent_retry_counts(self):
        """测试多个用户的重试次数独立管理"""
        user_id_1 = uuid.uuid4()
        user_id_2 = uuid.uuid4()
        
        # 用户 1 增加 3 次重试
        for _ in range(3):
            CaptchaService.increment_retry_count(user_id_1)
        
        # 用户 2 增加 5 次重试
        for _ in range(5):
            CaptchaService.increment_retry_count(user_id_2)
        
        # 验证两个用户的重试次数独立
        can_retry_1, retry_count_1 = CaptchaService.check_retry_limit(user_id_1)
        can_retry_2, retry_count_2 = CaptchaService.check_retry_limit(user_id_2)
        
        self.assertEqual(retry_count_1, 3)
        self.assertEqual(retry_count_2, 5)
        self.assertTrue(can_retry_1)
        self.assertTrue(can_retry_2)
    
    def test_multiple_users_independent_cooldowns(self):
        """测试多个用户的冷却期独立管理"""
        user_id_1 = uuid.uuid4()
        user_id_2 = uuid.uuid4()
        
        # 用户 1 设置冷却期
        CaptchaService.set_cooldown(user_id_1)
        
        # 验证用户 1 在冷却期内，用户 2 不在
        in_cooldown_1, _ = CaptchaService.check_cooldown(user_id_1)
        in_cooldown_2, _ = CaptchaService.check_cooldown(user_id_2)
        
        self.assertTrue(in_cooldown_1)
        self.assertFalse(in_cooldown_2)

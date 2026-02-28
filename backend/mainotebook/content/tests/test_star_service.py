"""收藏服务单元测试

测试收藏服务的各项功能，包括：
- 收藏内容（验证目标存在性、防重复收藏）
- 取消收藏内容（减少收藏计数）
- 获取用户收藏列表（按类型筛选）
- 获取收藏统计（按类型分组）
- 收藏计数更新（增加和减少）

验证需求：5.1, 5.2, 5.7, 5.10
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from mainotebook.system.models import Users
from ..models import StarRecord, KnowledgeBase, PersonaCard
from ..services.star_service import StarService


class StarServiceTest(TestCase):
    """收藏服务单元测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建测试用户
        self.user1 = Users.objects.create(
            username="testuser1",
            name="测试用户1",
            email="test1@example.com"
        )
        self.user2 = Users.objects.create(
            username="testuser2",
            name="测试用户2",
            email="test2@example.com"
        )
        
        # 创建测试知识库
        self.knowledge_base = KnowledgeBase.objects.create(
            name="测试知识库",
            description="用于测试收藏",
            uploader=self.user1,
            is_public=True,
            is_pending=False
        )
        
        # 创建测试人设卡
        self.persona_card = PersonaCard.objects.create(
            name="测试人设卡",
            description="用于测试收藏",
            uploader=self.user1,
            is_public=True,
            is_pending=False
        )
    
    def tearDown(self):
        """测试后清理"""
        # 清理测试数据
        StarRecord.objects.all().delete()
        KnowledgeBase.objects.all().delete()
        PersonaCard.objects.all().delete()
        Users.objects.all().delete()
    
    # ========== 收藏知识库测试 ==========
    
    def test_star_knowledge_base(self):
        """测试收藏知识库（需求 5.1）"""
        # 收藏知识库
        StarService.star_content(
            self.user2,
            str(self.knowledge_base.id),
            'knowledge'
        )
        
        # 验证收藏记录创建成功
        star_record = StarRecord.objects.filter(
            user=self.user2,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge'
        ).first()
        self.assertIsNotNone(star_record)
        
        # 验证知识库收藏计数增加
        self.knowledge_base.refresh_from_db()
        self.assertEqual(self.knowledge_base.star_count, 1)
    
    def test_star_knowledge_base_duplicate(self):
        """测试重复收藏知识库应该失败（需求 5.7, 5.10）"""
        # 第一次收藏
        StarService.star_content(
            self.user2,
            str(self.knowledge_base.id),
            'knowledge'
        )
        
        # 第二次收藏应该失败
        with self.assertRaises(ValidationError) as context:
            StarService.star_content(
                self.user2,
                str(self.knowledge_base.id),
                'knowledge'
            )
        
        self.assertIn("已经收藏", str(context.exception))
        
        # 验证收藏计数没有重复增加
        self.knowledge_base.refresh_from_db()
        self.assertEqual(self.knowledge_base.star_count, 1)
        
        # 验证只有一条收藏记录
        star_count = StarRecord.objects.filter(
            user=self.user2,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge'
        ).count()
        self.assertEqual(star_count, 1)
    
    def test_star_nonexistent_knowledge_base(self):
        """测试收藏不存在的知识库应该失败（需求 5.1）"""
        import uuid
        nonexistent_id = str(uuid.uuid4())
        
        # 尝试收藏不存在的知识库
        with self.assertRaises(ValidationError) as context:
            StarService.star_content(
                self.user2,
                nonexistent_id,
                'knowledge'
            )
        
        self.assertIn("不存在", str(context.exception))
        
        # 验证没有创建收藏记录
        star_count = StarRecord.objects.filter(
            user=self.user2,
            target_id=nonexistent_id,
            target_type='knowledge'
        ).count()
        self.assertEqual(star_count, 0)
    
    def test_multiple_users_star_knowledge_base(self):
        """测试多个用户收藏同一知识库（需求 5.1）"""
        # 用户1收藏
        StarService.star_content(
            self.user1,
            str(self.knowledge_base.id),
            'knowledge'
        )
        
        # 用户2收藏
        StarService.star_content(
            self.user2,
            str(self.knowledge_base.id),
            'knowledge'
        )
        
        # 验证收藏计数
        self.knowledge_base.refresh_from_db()
        self.assertEqual(self.knowledge_base.star_count, 2)
        
        # 验证收藏记录数
        star_count = StarRecord.objects.filter(
            target_id=str(self.knowledge_base.id),
            target_type='knowledge'
        ).count()
        self.assertEqual(star_count, 2)
    
    # ========== 取消收藏知识库测试 ==========
    
    def test_unstar_knowledge_base(self):
        """测试取消收藏知识库（需求 5.2）"""
        # 先收藏
        StarService.star_content(
            self.user2,
            str(self.knowledge_base.id),
            'knowledge'
        )
        
        # 验证收藏成功
        self.knowledge_base.refresh_from_db()
        self.assertEqual(self.knowledge_base.star_count, 1)
        
        # 取消收藏
        StarService.unstar_content(
            self.user2,
            str(self.knowledge_base.id),
            'knowledge'
        )
        
        # 验证收藏记录被删除
        star_exists = StarRecord.objects.filter(
            user=self.user2,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge'
        ).exists()
        self.assertFalse(star_exists)
        
        # 验证知识库收藏计数减少
        self.knowledge_base.refresh_from_db()
        self.assertEqual(self.knowledge_base.star_count, 0)
    
    def test_unstar_knowledge_base_without_star(self):
        """测试取消未收藏的知识库不会影响计数（需求 5.2）"""
        # 直接取消收藏（用户未收藏过）
        StarService.unstar_content(
            self.user2,
            str(self.knowledge_base.id),
            'knowledge'
        )
        
        # 验证知识库收藏计数不变
        self.knowledge_base.refresh_from_db()
        self.assertEqual(self.knowledge_base.star_count, 0)
    
    def test_unstar_knowledge_base_does_not_go_negative(self):
        """测试取消收藏不会使计数变为负数（需求 5.2）"""
        # 手动设置收藏计数为0
        self.knowledge_base.star_count = 0
        self.knowledge_base.save()
        
        # 创建收藏记录（模拟数据不一致的情况）
        StarRecord.objects.create(
            user=self.user2,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge'
        )
        
        # 取消收藏
        StarService.unstar_content(
            self.user2,
            str(self.knowledge_base.id),
            'knowledge'
        )
        
        # 验证收藏计数不会变为负数
        self.knowledge_base.refresh_from_db()
        self.assertEqual(self.knowledge_base.star_count, 0)
    
    def test_unstar_knowledge_base_by_one_user_does_not_affect_others(self):
        """测试一个用户取消收藏不影响其他用户的收藏（需求 5.2）"""
        # 两个用户都收藏
        StarService.star_content(
            self.user1,
            str(self.knowledge_base.id),
            'knowledge'
        )
        StarService.star_content(
            self.user2,
            str(self.knowledge_base.id),
            'knowledge'
        )
        
        # 验证收藏计数
        self.knowledge_base.refresh_from_db()
        self.assertEqual(self.knowledge_base.star_count, 2)
        
        # 用户2取消收藏
        StarService.unstar_content(
            self.user2,
            str(self.knowledge_base.id),
            'knowledge'
        )
        
        # 验证收藏计数减少1
        self.knowledge_base.refresh_from_db()
        self.assertEqual(self.knowledge_base.star_count, 1)
        
        # 验证用户1的收藏记录仍然存在
        user1_star_exists = StarRecord.objects.filter(
            user=self.user1,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge'
        ).exists()
        self.assertTrue(user1_star_exists)
        
        # 验证用户2的收藏记录被删除
        user2_star_exists = StarRecord.objects.filter(
            user=self.user2,
            target_id=str(self.knowledge_base.id),
            target_type='knowledge'
        ).exists()
        self.assertFalse(user2_star_exists)
    
    # ========== 收藏人设卡测试 ==========
    
    def test_star_persona_card(self):
        """测试收藏人设卡（需求 5.3）"""
        # 收藏人设卡
        StarService.star_content(
            self.user2,
            str(self.persona_card.id),
            'persona'
        )
        
        # 验证收藏记录创建成功
        star_record = StarRecord.objects.filter(
            user=self.user2,
            target_id=str(self.persona_card.id),
            target_type='persona'
        ).first()
        self.assertIsNotNone(star_record)
        
        # 验证人设卡收藏计数增加
        self.persona_card.refresh_from_db()
        self.assertEqual(self.persona_card.star_count, 1)
    
    def test_star_persona_card_duplicate(self):
        """测试重复收藏人设卡应该失败（需求 5.7, 5.10）"""
        # 第一次收藏
        StarService.star_content(
            self.user2,
            str(self.persona_card.id),
            'persona'
        )
        
        # 第二次收藏应该失败
        with self.assertRaises(ValidationError) as context:
            StarService.star_content(
                self.user2,
                str(self.persona_card.id),
                'persona'
            )
        
        self.assertIn("已经收藏", str(context.exception))
        
        # 验证收藏计数没有重复增加
        self.persona_card.refresh_from_db()
        self.assertEqual(self.persona_card.star_count, 1)
    
    def test_star_nonexistent_persona_card(self):
        """测试收藏不存在的人设卡应该失败（需求 5.3）"""
        import uuid
        nonexistent_id = str(uuid.uuid4())
        
        # 尝试收藏不存在的人设卡
        with self.assertRaises(ValidationError) as context:
            StarService.star_content(
                self.user2,
                nonexistent_id,
                'persona'
            )
        
        self.assertIn("不存在", str(context.exception))
    
    # ========== 取消收藏人设卡测试 ==========
    
    def test_unstar_persona_card(self):
        """测试取消收藏人设卡（需求 5.4）"""
        # 先收藏
        StarService.star_content(
            self.user2,
            str(self.persona_card.id),
            'persona'
        )
        
        # 验证收藏成功
        self.persona_card.refresh_from_db()
        self.assertEqual(self.persona_card.star_count, 1)
        
        # 取消收藏
        StarService.unstar_content(
            self.user2,
            str(self.persona_card.id),
            'persona'
        )
        
        # 验证收藏记录被删除
        star_exists = StarRecord.objects.filter(
            user=self.user2,
            target_id=str(self.persona_card.id),
            target_type='persona'
        ).exists()
        self.assertFalse(star_exists)
        
        # 验证人设卡收藏计数减少
        self.persona_card.refresh_from_db()
        self.assertEqual(self.persona_card.star_count, 0)
    
    def test_unstar_persona_card_without_star(self):
        """测试取消未收藏的人设卡不会影响计数（需求 5.4）"""
        # 直接取消收藏（用户未收藏过）
        StarService.unstar_content(
            self.user2,
            str(self.persona_card.id),
            'persona'
        )
        
        # 验证人设卡收藏计数不变
        self.persona_card.refresh_from_db()
        self.assertEqual(self.persona_card.star_count, 0)
    
    # ========== 无效目标类型测试 ==========
    
    def test_star_with_invalid_target_type(self):
        """测试使用无效的目标类型收藏应该失败（需求 5.1）"""
        # 尝试使用无效的目标类型
        with self.assertRaises(ValidationError) as context:
            StarService.star_content(
                self.user2,
                str(self.knowledge_base.id),
                'invalid_type'
            )
        
        self.assertIn("无效", str(context.exception))
        
        # 验证没有创建收藏记录
        star_count = StarRecord.objects.filter(user=self.user2).count()
        self.assertEqual(star_count, 0)
    
    # ========== 获取用户收藏列表测试 ==========
    
    def test_get_user_stars_empty(self):
        """测试获取空收藏列表（需求 5.5）"""
        # 获取用户收藏列表
        queryset = StarService.get_user_stars(self.user2)
        
        # 验证结果为空
        self.assertEqual(queryset.count(), 0)
    
    def test_get_user_stars_all(self):
        """测试获取用户所有收藏（需求 5.5）"""
        # 用户2收藏知识库和人设卡
        StarService.star_content(
            self.user2,
            str(self.knowledge_base.id),
            'knowledge'
        )
        StarService.star_content(
            self.user2,
            str(self.persona_card.id),
            'persona'
        )
        
        # 获取用户收藏列表
        queryset = StarService.get_user_stars(self.user2)
        
        # 验证结果
        self.assertEqual(queryset.count(), 2)
        
        # 验证收藏记录
        target_ids = [str(star.target_id) for star in queryset]
        self.assertIn(str(self.knowledge_base.id), target_ids)
        self.assertIn(str(self.persona_card.id), target_ids)
    
    def test_get_user_stars_filter_by_knowledge(self):
        """测试按类型筛选收藏列表（知识库）（需求 5.5）"""
        # 用户2收藏知识库和人设卡
        StarService.star_content(
            self.user2,
            str(self.knowledge_base.id),
            'knowledge'
        )
        StarService.star_content(
            self.user2,
            str(self.persona_card.id),
            'persona'
        )
        
        # 获取知识库收藏列表
        queryset = StarService.get_user_stars(self.user2, target_type='knowledge')
        
        # 验证结果
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().target_type, 'knowledge')
        self.assertEqual(str(queryset.first().target_id), str(self.knowledge_base.id))
    
    def test_get_user_stars_filter_by_persona(self):
        """测试按类型筛选收藏列表（人设卡）（需求 5.5）"""
        # 用户2收藏知识库和人设卡
        StarService.star_content(
            self.user2,
            str(self.knowledge_base.id),
            'knowledge'
        )
        StarService.star_content(
            self.user2,
            str(self.persona_card.id),
            'persona'
        )
        
        # 获取人设卡收藏列表
        queryset = StarService.get_user_stars(self.user2, target_type='persona')
        
        # 验证结果
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().target_type, 'persona')
        self.assertEqual(str(queryset.first().target_id), str(self.persona_card.id))
    
    def test_get_user_stars_ordering(self):
        """测试收藏列表按创建时间倒序排列（需求 5.5）"""
        # 创建另一个知识库
        kb2 = KnowledgeBase.objects.create(
            name="第二个知识库",
            description="描述",
            uploader=self.user1
        )
        
        # 用户2依次收藏
        StarService.star_content(
            self.user2,
            str(self.knowledge_base.id),
            'knowledge'
        )
        StarService.star_content(
            self.user2,
            str(kb2.id),
            'knowledge'
        )
        
        # 获取收藏列表
        queryset = StarService.get_user_stars(self.user2)
        star_list = list(queryset)
        
        # 验证排序（最新的在前）
        self.assertEqual(len(star_list), 2)
        self.assertEqual(str(star_list[0].target_id), str(kb2.id))  # 最新的
        self.assertEqual(str(star_list[1].target_id), str(self.knowledge_base.id))  # 最早的
    
    def test_get_user_stars_only_returns_own_stars(self):
        """测试收藏列表只返回用户自己的收藏（需求 5.5）"""
        # 用户1收藏知识库
        StarService.star_content(
            self.user1,
            str(self.knowledge_base.id),
            'knowledge'
        )
        
        # 用户2收藏人设卡
        StarService.star_content(
            self.user2,
            str(self.persona_card.id),
            'persona'
        )
        
        # 获取用户2的收藏列表
        queryset = StarService.get_user_stars(self.user2)
        
        # 验证结果只包含用户2的收藏
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().target_type, 'persona')
        self.assertEqual(str(queryset.first().target_id), str(self.persona_card.id))
    
    # ========== 获取收藏统计测试 ==========
    
    def test_get_star_stats_empty(self):
        """测试获取空收藏统计（需求 5.6）"""
        # 获取收藏统计
        stats = StarService.get_star_stats(self.user2)
        
        # 验证结果
        self.assertEqual(stats['total'], 0)
        self.assertEqual(stats['knowledge'], 0)
        self.assertEqual(stats['persona'], 0)
    
    def test_get_star_stats_with_data(self):
        """测试获取收藏统计（需求 5.6）"""
        # 创建更多测试数据
        kb2 = KnowledgeBase.objects.create(
            name="第二个知识库",
            description="描述",
            uploader=self.user1
        )
        pc2 = PersonaCard.objects.create(
            name="第二个人设卡",
            description="描述",
            uploader=self.user1
        )
        
        # 用户2收藏多个内容
        StarService.star_content(self.user2, str(self.knowledge_base.id), 'knowledge')
        StarService.star_content(self.user2, str(kb2.id), 'knowledge')
        StarService.star_content(self.user2, str(self.persona_card.id), 'persona')
        StarService.star_content(self.user2, str(pc2.id), 'persona')
        
        # 获取收藏统计
        stats = StarService.get_star_stats(self.user2)
        
        # 验证结果
        self.assertEqual(stats['total'], 4)
        self.assertEqual(stats['knowledge'], 2)
        self.assertEqual(stats['persona'], 2)
    
    def test_get_star_stats_only_counts_own_stars(self):
        """测试收藏统计只计算用户自己的收藏（需求 5.6）"""
        # 用户1收藏知识库
        StarService.star_content(
            self.user1,
            str(self.knowledge_base.id),
            'knowledge'
        )
        
        # 用户2收藏人设卡
        StarService.star_content(
            self.user2,
            str(self.persona_card.id),
            'persona'
        )
        
        # 获取用户2的收藏统计
        stats = StarService.get_star_stats(self.user2)
        
        # 验证结果只包含用户2的收藏
        self.assertEqual(stats['total'], 1)
        self.assertEqual(stats['knowledge'], 0)
        self.assertEqual(stats['persona'], 1)
    
    # ========== 收藏和取消收藏往返测试 ==========
    
    def test_star_unstar_roundtrip(self):
        """测试收藏和取消收藏的往返操作（需求 5.1, 5.2）"""
        # 初始状态
        self.assertEqual(self.knowledge_base.star_count, 0)
        
        # 收藏
        StarService.star_content(
            self.user2,
            str(self.knowledge_base.id),
            'knowledge'
        )
        self.knowledge_base.refresh_from_db()
        self.assertEqual(self.knowledge_base.star_count, 1)
        
        # 取消收藏
        StarService.unstar_content(
            self.user2,
            str(self.knowledge_base.id),
            'knowledge'
        )
        self.knowledge_base.refresh_from_db()
        self.assertEqual(self.knowledge_base.star_count, 0)
        
        # 再次收藏
        StarService.star_content(
            self.user2,
            str(self.knowledge_base.id),
            'knowledge'
        )
        self.knowledge_base.refresh_from_db()
        self.assertEqual(self.knowledge_base.star_count, 1)

"""审核服务单元测试

测试审核服务的各项功能，包括：
- 获取待审核列表（按类型过滤、搜索）
- 批准内容（状态更新、上传记录更新）
- 拒绝内容（状态更新、记录拒绝原因）
- 退回内容（状态更新）
- 获取审核统计数据
- 权限验证

验证需求：3.1, 3.2, 3.3, 3.4, 3.11, 3.12
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from mainotebook.system.models import Users
from ..models import KnowledgeBase, PersonaCard, UploadRecord
from ..services.review_service import ReviewService


class ReviewServiceTest(TestCase):
    """审核服务单元测试类"""
    
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
        self.reviewer = Users.objects.create(
            username="reviewer",
            name="审核员",
            email="reviewer@example.com",
            is_staff=True
        )
    
    def tearDown(self):
        """测试后清理"""
        # 清理测试数据
        UploadRecord.objects.all().delete()
        KnowledgeBase.objects.all().delete()
        PersonaCard.objects.all().delete()
        Users.objects.all().delete()
    
    # ========== 获取待审核列表测试 ==========
    
    def test_get_pending_items_empty(self):
        """测试获取空的待审核列表（需求 3.1）"""
        result = ReviewService.get_pending_items()
        items = result['items']
        
        # 验证结果为空
        self.assertEqual(len(items), 0)
        self.assertEqual(result['total'], 0)
    
    def test_get_pending_items_with_knowledge_bases(self):
        """测试获取待审核的知识库列表（需求 3.1）"""
        # 创建待审核的知识库
        kb1 = KnowledgeBase.objects.create(
            name='待审核知识库1',
            description='描述1',
            uploader=self.user1,
            is_pending=True,
            is_public=False
        )
        kb2 = KnowledgeBase.objects.create(
            name='待审核知识库2',
            description='描述2',
            uploader=self.user2,
            is_pending=True,
            is_public=False
        )
        
        # 创建非待审核的知识库（不应出现在结果中）
        KnowledgeBase.objects.create(
            name='已发布知识库',
            description='描述',
            uploader=self.user1,
            is_pending=False,
            is_public=True
        )
        
        # 获取待审核列表
        result = ReviewService.get_pending_items()
        items = result['items']
        
        # 验证结果
        self.assertEqual(len(items), 2)
        
        # 验证包含正确的知识库
        kb_ids = [item['id'] for item in items]
        self.assertIn(kb1.id, kb_ids)
        self.assertIn(kb2.id, kb_ids)
        
        # 验证数据结构
        for item in items:
            self.assertIn('id', item)
            self.assertIn('name', item)
            self.assertIn('description', item)
            self.assertIn('content_type', item)
            self.assertIn('uploader_id', item)
            self.assertIn('uploader_name', item)
            self.assertIn('create_datetime', item)
            self.assertIn('tags', item)
            self.assertIn('file_count', item)
            self.assertEqual(item['content_type'], 'knowledge')
    
    def test_get_pending_items_with_persona_cards(self):
        """测试获取待审核的人设卡列表（需求 3.1）"""
        # 创建待审核的人设卡
        pc1 = PersonaCard.objects.create(
            name='待审核人设卡1',
            description='描述1',
            uploader=self.user1,
            is_pending=True,
            is_public=False
        )
        pc2 = PersonaCard.objects.create(
            name='待审核人设卡2',
            description='描述2',
            uploader=self.user2,
            is_pending=True,
            is_public=False
        )
        
        # 创建非待审核的人设卡（不应出现在结果中）
        PersonaCard.objects.create(
            name='已发布人设卡',
            description='描述',
            uploader=self.user1,
            is_pending=False,
            is_public=True
        )
        
        # 获取待审核列表
        result = ReviewService.get_pending_items()
        items = result['items']
        
        # 验证结果
        self.assertEqual(len(items), 2)
        
        # 验证包含正确的人设卡
        pc_ids = [item['id'] for item in items]
        self.assertIn(pc1.id, pc_ids)
        self.assertIn(pc2.id, pc_ids)
        
        # 验证内容类型
        for item in items:
            self.assertEqual(item['content_type'], 'persona')
    
    def test_get_pending_items_mixed_content_types(self):
        """测试获取混合类型的待审核列表（需求 3.1）"""
        # 创建待审核的知识库
        kb = KnowledgeBase.objects.create(
            name='待审核知识库',
            description='描述',
            uploader=self.user1,
            is_pending=True
        )
        
        # 创建待审核的人设卡
        pc = PersonaCard.objects.create(
            name='待审核人设卡',
            description='描述',
            uploader=self.user2,
            is_pending=True
        )
        
        # 获取待审核列表
        result = ReviewService.get_pending_items()
        items = result['items']
        
        # 验证结果包含两种类型
        self.assertEqual(len(items), 2)
        
        content_types = [item['content_type'] for item in items]
        self.assertIn('knowledge', content_types)
        self.assertIn('persona', content_types)
    
    def test_get_pending_items_filter_by_content_type(self):
        """测试按内容类型过滤待审核列表（需求 3.1）"""
        # 创建待审核的知识库
        kb = KnowledgeBase.objects.create(
            name='待审核知识库',
            description='描述',
            uploader=self.user1,
            is_pending=True
        )
        
        # 创建待审核的人设卡
        pc = PersonaCard.objects.create(
            name='待审核人设卡',
            description='描述',
            uploader=self.user2,
            is_pending=True
        )
        
        # 只获取知识库
        result = ReviewService.get_pending_items(filters={'content_type': 'knowledge'})
        items = result['items']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['content_type'], 'knowledge')
        self.assertEqual(items[0]['id'], kb.id)
        
        # 只获取人设卡
        result = ReviewService.get_pending_items(filters={'content_type': 'persona'})
        items = result['items']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['content_type'], 'persona')
        self.assertEqual(items[0]['id'], pc.id)
    
    def test_get_pending_items_search(self):
        """测试搜索待审核列表（需求 3.1）"""
        # 创建待审核的知识库
        KnowledgeBase.objects.create(
            name='Python教程',
            description='学习Python编程',
            uploader=self.user1,
            is_pending=True
        )
        KnowledgeBase.objects.create(
            name='Django框架',
            description='Web开发框架',
            uploader=self.user2,
            is_pending=True
        )
        
        # 搜索包含 "Python" 的内容
        result = ReviewService.get_pending_items(filters={'search': 'Python'})
        items = result['items']
        
        # 验证结果
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['name'], 'Python教程')
    
    def test_get_pending_items_ordering(self):
        """测试待审核列表按创建时间倒序排序（需求 3.1）"""
        # 创建多个待审核的知识库
        kb1 = KnowledgeBase.objects.create(
            name='最早的知识库',
            description='描述',
            uploader=self.user1,
            is_pending=True
        )
        kb2 = KnowledgeBase.objects.create(
            name='中间的知识库',
            description='描述',
            uploader=self.user1,
            is_pending=True
        )
        kb3 = KnowledgeBase.objects.create(
            name='最新的知识库',
            description='描述',
            uploader=self.user1,
            is_pending=True
        )
        
        # 获取待审核列表
        result = ReviewService.get_pending_items()
        items = result['items']
        
        # 验证排序（最新的在前）
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]['id'], kb3.id)
        self.assertEqual(items[1]['id'], kb2.id)
        self.assertEqual(items[2]['id'], kb1.id)
    
    # ========== 批准内容测试 ==========
    
    def test_approve_knowledge_base(self):
        """测试批准知识库（需求 3.2）"""
        # 创建待审核的知识库
        kb = KnowledgeBase.objects.create(
            name='待审核知识库',
            description='描述',
            uploader=self.user1,
            is_pending=True,
            is_public=False
        )
        
        # 创建上传记录
        UploadRecord.objects.create(
            uploader=self.user1,
            target_id=str(kb.id),
            target_type='knowledge',
            name=kb.name,
            description=kb.description,
            status='pending'
        )
        
        # 批准内容
        ReviewService.approve_content(str(kb.id), 'knowledge', self.reviewer)
        
        # 验证知识库状态更新
        kb.refresh_from_db()
        self.assertFalse(kb.is_pending)
        self.assertTrue(kb.is_public)
        self.assertIsNone(kb.rejection_reason)
        
        # 验证上传记录状态更新
        upload_record = UploadRecord.objects.get(
            target_id=str(kb.id),
            target_type='knowledge'
        )
        self.assertEqual(upload_record.status, 'approved')
    
    def test_approve_persona_card(self):
        """测试批准人设卡（需求 3.2）"""
        # 创建待审核的人设卡
        pc = PersonaCard.objects.create(
            name='待审核人设卡',
            description='描述',
            uploader=self.user1,
            is_pending=True,
            is_public=False
        )
        
        # 创建上传记录
        UploadRecord.objects.create(
            uploader=self.user1,
            target_id=str(pc.id),
            target_type='persona',
            name=pc.name,
            description=pc.description,
            status='pending'
        )
        
        # 批准内容
        ReviewService.approve_content(str(pc.id), 'persona', self.reviewer)
        
        # 验证人设卡状态更新
        pc.refresh_from_db()
        self.assertFalse(pc.is_pending)
        self.assertTrue(pc.is_public)
        self.assertIsNone(pc.rejection_reason)
        
        # 验证上传记录状态更新
        upload_record = UploadRecord.objects.get(
            target_id=str(pc.id),
            target_type='persona'
        )
        self.assertEqual(upload_record.status, 'approved')
    
    def test_approve_content_with_invalid_type(self):
        """测试批准无效类型的内容应该失败（需求 3.2）"""
        # 创建知识库
        kb = KnowledgeBase.objects.create(
            name='知识库',
            description='描述',
            uploader=self.user1,
            is_pending=True
        )
        
        # 尝试使用无效的内容类型
        with self.assertRaises(ValidationError) as context:
            ReviewService.approve_content(str(kb.id), 'invalid_type', self.reviewer)
        
        self.assertIn("无效", str(context.exception))
    
    def test_approve_nonexistent_content(self):
        """测试批准不存在的内容应该失败（需求 3.2）"""
        import uuid
        nonexistent_id = str(uuid.uuid4())
        
        # 尝试批准不存在的内容
        with self.assertRaises(ValidationError) as context:
            ReviewService.approve_content(nonexistent_id, 'knowledge', self.reviewer)
        
        self.assertIn("不存在", str(context.exception))
    
    def test_approve_content_not_pending(self):
        """测试批准非待审核状态的内容应该失败（需求 3.2）"""
        # 创建已发布的知识库
        kb = KnowledgeBase.objects.create(
            name='已发布知识库',
            description='描述',
            uploader=self.user1,
            is_pending=False,
            is_public=True
        )
        
        # 尝试批准
        with self.assertRaises(ValidationError) as context:
            ReviewService.approve_content(str(kb.id), 'knowledge', self.reviewer)
        
        self.assertIn("待审核", str(context.exception))
    
    # ========== 拒绝内容测试 ==========
    
    def test_reject_knowledge_base(self):
        """测试拒绝知识库（需求 3.3）"""
        # 创建待审核的知识库
        kb = KnowledgeBase.objects.create(
            name='待审核知识库',
            description='描述',
            uploader=self.user1,
            is_pending=True,
            is_public=False
        )
        
        # 创建上传记录
        UploadRecord.objects.create(
            uploader=self.user1,
            target_id=str(kb.id),
            target_type='knowledge',
            name=kb.name,
            description=kb.description,
            status='pending'
        )
        
        # 拒绝内容
        reason = '内容不符合规范'
        ReviewService.reject_content(str(kb.id), 'knowledge', self.reviewer, reason)
        
        # 验证知识库状态更新
        kb.refresh_from_db()
        self.assertFalse(kb.is_pending)
        self.assertFalse(kb.is_public)
        self.assertEqual(kb.rejection_reason, reason)
        
        # 验证上传记录状态更新
        upload_record = UploadRecord.objects.get(
            target_id=str(kb.id),
            target_type='knowledge'
        )
        self.assertEqual(upload_record.status, 'rejected')
    
    def test_reject_persona_card(self):
        """测试拒绝人设卡（需求 3.3）"""
        # 创建待审核的人设卡
        pc = PersonaCard.objects.create(
            name='待审核人设卡',
            description='描述',
            uploader=self.user1,
            is_pending=True,
            is_public=False
        )
        
        # 创建上传记录
        UploadRecord.objects.create(
            uploader=self.user1,
            target_id=str(pc.id),
            target_type='persona',
            name=pc.name,
            description=pc.description,
            status='pending'
        )
        
        # 拒绝内容
        reason = 'TOML 配置文件格式错误'
        ReviewService.reject_content(str(pc.id), 'persona', self.reviewer, reason)
        
        # 验证人设卡状态更新
        pc.refresh_from_db()
        self.assertFalse(pc.is_pending)
        self.assertFalse(pc.is_public)
        self.assertEqual(pc.rejection_reason, reason)
        
        # 验证上传记录状态更新
        upload_record = UploadRecord.objects.get(
            target_id=str(pc.id),
            target_type='persona'
        )
        self.assertEqual(upload_record.status, 'rejected')
    
    def test_reject_content_without_reason(self):
        """测试拒绝内容时必须提供原因（需求 3.3）"""
        # 创建待审核的知识库
        kb = KnowledgeBase.objects.create(
            name='待审核知识库',
            description='描述',
            uploader=self.user1,
            is_pending=True
        )
        
        # 尝试拒绝但不提供原因
        with self.assertRaises(ValidationError) as context:
            ReviewService.reject_content(str(kb.id), 'knowledge', self.reviewer, '')
        
        self.assertIn("原因", str(context.exception))
        
        # 验证状态未改变
        kb.refresh_from_db()
        self.assertTrue(kb.is_pending)
    
    def test_reject_content_with_whitespace_reason(self):
        """测试拒绝内容时原因不能只包含空白字符（需求 3.3）"""
        # 创建待审核的知识库
        kb = KnowledgeBase.objects.create(
            name='待审核知识库',
            description='描述',
            uploader=self.user1,
            is_pending=True
        )
        
        # 尝试拒绝但原因只包含空白字符
        with self.assertRaises(ValidationError) as context:
            ReviewService.reject_content(str(kb.id), 'knowledge', self.reviewer, '   ')
        
        self.assertIn("原因", str(context.exception))
    
    def test_reject_content_not_pending(self):
        """测试拒绝非待审核状态的内容应该失败（需求 3.3）"""
        # 创建已发布的知识库
        kb = KnowledgeBase.objects.create(
            name='已发布知识库',
            description='描述',
            uploader=self.user1,
            is_pending=False,
            is_public=True
        )
        
        # 尝试拒绝
        with self.assertRaises(ValidationError) as context:
            ReviewService.reject_content(
                str(kb.id), 'knowledge', self.reviewer, '拒绝原因'
            )
        
        self.assertIn("待审核", str(context.exception))
    
    # ========== 退回内容测试 ==========
    
    def test_return_knowledge_base(self):
        """测试退回知识库（需求 3.4）"""
        # 创建待审核的知识库
        kb = KnowledgeBase.objects.create(
            name='待审核知识库',
            description='描述',
            uploader=self.user1,
            is_pending=True,
            is_public=False
        )
        
        # 退回内容
        reason = '请补充更多信息'
        ReviewService.return_content(str(kb.id), 'knowledge', self.reviewer, reason)
        
        # 验证知识库状态更新（退回到草稿状态）
        kb.refresh_from_db()
        self.assertFalse(kb.is_pending)
        self.assertFalse(kb.is_public)
        self.assertEqual(kb.rejection_reason, reason)
    
    def test_return_persona_card(self):
        """测试退回人设卡（需求 3.4）"""
        # 创建待审核的人设卡
        pc = PersonaCard.objects.create(
            name='待审核人设卡',
            description='描述',
            uploader=self.user1,
            is_pending=True,
            is_public=False
        )
        
        # 退回内容
        reason = '请修改描述'
        ReviewService.return_content(str(pc.id), 'persona', self.reviewer, reason)
        
        # 验证人设卡状态更新
        pc.refresh_from_db()
        self.assertFalse(pc.is_pending)
        self.assertFalse(pc.is_public)
        self.assertEqual(pc.rejection_reason, reason)
    
    def test_return_content_not_pending(self):
        """测试退回非待审核状态的内容应该失败（需求 3.4）"""
        # 创建已发布的知识库
        kb = KnowledgeBase.objects.create(
            name='已发布知识库',
            description='描述',
            uploader=self.user1,
            is_pending=False,
            is_public=True
        )
        
        # 尝试退回
        with self.assertRaises(ValidationError) as context:
            ReviewService.return_content(
                str(kb.id), 'knowledge', self.reviewer, '退回原因'
            )
        
        self.assertIn("待审核", str(context.exception))
    
    # ========== 获取审核统计数据测试 ==========
    
    def test_get_review_stats_empty(self):
        """测试获取空的审核统计数据（需求 3.11）"""
        stats = ReviewService.get_review_stats()
        
        # 验证统计数据结构
        self.assertIn('pending_count', stats)
        self.assertIn('pending_knowledge', stats)
        self.assertIn('pending_persona', stats)
        self.assertIn('approved_today', stats)
        self.assertIn('rejected_today', stats)
        self.assertIn('pass_rate', stats)
        
        # 验证所有计数为0
        self.assertEqual(stats['pending_count'], 0)
        self.assertEqual(stats['pending_knowledge'], 0)
        self.assertEqual(stats['pending_persona'], 0)
        self.assertEqual(stats['approved_today'], 0)
        self.assertEqual(stats['rejected_today'], 0)
        self.assertEqual(stats['pass_rate'], 0)
    
    def test_get_review_stats_with_pending_items(self):
        """测试获取包含待审核项的统计数据（需求 3.11）"""
        # 创建待审核的知识库
        KnowledgeBase.objects.create(
            name='待审核知识库1',
            description='描述',
            uploader=self.user1,
            is_pending=True
        )
        KnowledgeBase.objects.create(
            name='待审核知识库2',
            description='描述',
            uploader=self.user1,
            is_pending=True
        )
        
        # 创建待审核的人设卡
        PersonaCard.objects.create(
            name='待审核人设卡',
            description='描述',
            uploader=self.user2,
            is_pending=True
        )
        
        # 获取统计数据
        stats = ReviewService.get_review_stats()
        
        # 验证待审核数量
        self.assertEqual(stats['pending_count'], 3)
        self.assertEqual(stats['pending_knowledge'], 2)
        self.assertEqual(stats['pending_persona'], 1)
    
    def test_get_review_stats_with_today_reviews(self):
        """测试获取包含今日审核数据的统计（需求 3.11）"""
        # 创建今日批准的上传记录
        kb1 = KnowledgeBase.objects.create(
            name='已批准知识库',
            description='描述',
            uploader=self.user1,
            is_pending=False,
            is_public=True
        )
        UploadRecord.objects.create(
            uploader=self.user1,
            target_id=str(kb1.id),
            target_type='knowledge',
            name=kb1.name,
            description=kb1.description,
            status='approved'
        )
        
        # 创建今日拒绝的上传记录
        kb2 = KnowledgeBase.objects.create(
            name='已拒绝知识库',
            description='描述',
            uploader=self.user2,
            is_pending=False,
            is_public=False
        )
        UploadRecord.objects.create(
            uploader=self.user2,
            target_id=str(kb2.id),
            target_type='knowledge',
            name=kb2.name,
            description=kb2.description,
            status='rejected'
        )
        
        # 获取统计数据
        stats = ReviewService.get_review_stats()
        
        # 验证今日审核数量
        self.assertEqual(stats['approved_today'], 1)
        self.assertEqual(stats['rejected_today'], 1)
    
    def test_get_review_stats_pass_rate(self):
        """测试获取通过率统计（需求 3.11）"""
        # 创建最近 30 天内的审核记录
        now = timezone.now()
        
        # 批准的记录（3条）
        for i in range(3):
            kb = KnowledgeBase.objects.create(
                name=f'已批准知识库{i}',
                description='描述',
                uploader=self.user1,
                is_pending=False,
                is_public=True
            )
            record = UploadRecord.objects.create(
                uploader=self.user1,
                target_id=str(kb.id),
                target_type='knowledge',
                name=kb.name,
                description=kb.description,
                status='approved'
            )
            # 设置更新时间为最近 30 天内
            record.update_datetime = now - timedelta(days=i)
            record.save()
        
        # 拒绝的记录（1条）
        kb = KnowledgeBase.objects.create(
            name='已拒绝知识库',
            description='描述',
            uploader=self.user2,
            is_pending=False,
            is_public=False
        )
        record = UploadRecord.objects.create(
            uploader=self.user2,
            target_id=str(kb.id),
            target_type='knowledge',
            name=kb.name,
            description=kb.description,
            status='rejected'
        )
        record.update_datetime = now - timedelta(days=5)
        record.save()
        
        # 获取统计数据
        stats = ReviewService.get_review_stats()
        
        # 验证通过率（3/4 = 75%）
        self.assertEqual(stats['pass_rate'], 75.0)
    
    def test_get_review_stats_excludes_old_records(self):
        """测试统计数据不包含 30 天前的记录（需求 3.11）"""
        # 创建 30 天前的审核记录
        kb = KnowledgeBase.objects.create(
            name='旧的知识库',
            description='描述',
            uploader=self.user1,
            is_pending=False,
            is_public=True
        )
        record = UploadRecord.objects.create(
            uploader=self.user1,
            target_id=str(kb.id),
            target_type='knowledge',
            name=kb.name,
            description=kb.description,
            status='approved'
        )
        # 使用 update 方法设置更新时间为 31 天前，避免 auto_now 自动更新
        UploadRecord.objects.filter(id=record.id).update(
            update_datetime=timezone.now() - timedelta(days=31)
        )
        
        # 获取统计数据
        stats = ReviewService.get_review_stats()
        
        # 验证通过率为 0（因为没有最近 30 天的记录）
        self.assertEqual(stats['pass_rate'], 0)

    # ========== 默认分页参数测试 ==========

    def test_get_pending_items_default_pagination(self):
        """测试默认分页参数 page=1, page_size=10（需求 1.3）"""
        # 创建 12 条待审核知识库
        for i in range(12):
            KnowledgeBase.objects.create(
                name=f'知识库_{i}',
                description='描述',
                uploader=self.user1,
                is_pending=True,
                is_public=False
            )

        # 不传分页参数，使用默认值
        result = ReviewService.get_pending_items()

        # 验证默认返回 10 条
        self.assertEqual(len(result['items']), 10)
        self.assertEqual(result['total'], 12)

    # ========== 内容不存在边界条件测试 ==========

    def test_approve_nonexistent_content_boundary(self):
        """测试审核通过不存在的内容（需求 2.5）"""
        import uuid
        fake_id = str(uuid.uuid4())

        with self.assertRaises(ValidationError) as context:
            ReviewService.approve_content(fake_id, 'knowledge', self.reviewer)
        self.assertIn("不存在", str(context.exception))

    def test_reject_nonexistent_content_boundary(self):
        """测试审核拒绝不存在的内容（需求 3.6）"""
        import uuid
        fake_id = str(uuid.uuid4())

        with self.assertRaises(ValidationError) as context:
            ReviewService.reject_content(fake_id, 'knowledge', self.reviewer, '拒绝原因')
        self.assertIn("不存在", str(context.exception))

    def test_return_nonexistent_content_boundary(self):
        """测试退回不存在的内容（需求 3.5）"""
        import uuid
        fake_id = str(uuid.uuid4())

        with self.assertRaises(ValidationError) as context:
            ReviewService.return_content(fake_id, 'knowledge', self.reviewer, '退回原因')
        self.assertIn("不存在", str(context.exception))

    # ========== reason 为空和超长的错误响应测试 ==========

    def test_reject_content_with_too_long_reason(self):
        """测试拒绝原因超过 500 字符（需求 3.4）"""
        kb = KnowledgeBase.objects.create(
            name='待审核知识库',
            description='描述',
            uploader=self.user1,
            is_pending=True
        )

        long_reason = 'A' * 501
        with self.assertRaises(ValidationError) as context:
            ReviewService.reject_content(str(kb.id), 'knowledge', self.reviewer, long_reason)
        self.assertIn("500", str(context.exception))

    def test_reject_content_with_empty_reason(self):
        """测试拒绝原因为空字符串（需求 3.3）"""
        kb = KnowledgeBase.objects.create(
            name='待审核知识库',
            description='描述',
            uploader=self.user1,
            is_pending=True
        )

        with self.assertRaises(ValidationError):
            ReviewService.reject_content(str(kb.id), 'knowledge', self.reviewer, '')

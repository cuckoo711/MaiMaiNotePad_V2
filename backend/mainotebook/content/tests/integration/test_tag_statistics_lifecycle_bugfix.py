# -*- coding: utf-8 -*-

"""
标签统计生命周期同步 Bug 探索测试

此测试文件用于展示标签统计生命周期同步的 bug。
测试在未修复的代码上运行，预期会失败，失败确认 bug 存在。

**重要提示**：
- 这些测试编码了期望行为
- 在未修复的代码上运行时应该失败
- 失败证明 bug 存在
- 在实现修复后，这些测试应该通过

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**
"""

from django.test import TestCase
from django.utils import timezone
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase

from mainotebook.system.models import Users
from mainotebook.content.models import PersonaCard, KnowledgeBase, TagStatistics
from mainotebook.content.services.tag_service import TagService


# 配置 Hypothesis
settings.register_profile("bugfix", max_examples=10, deadline=None)
settings.load_profile("bugfix")


class TagStatisticsLifecycleBugExplorationTest(TestCase):
    """标签统计生命周期同步 Bug 探索测试
    
    **Property 1: Fault Condition** - 标签统计生命周期同步失败
    
    此测试类展示 bug 的存在，通过具体的失败案例证明标签统计未正确同步。
    
    **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**
    """
    
    def setUp(self):
        """测试前准备"""
        # 创建测试用户（如果已存在则获取）
        self.user, _ = Users.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'name': '测试用户'
            }
        )
        
        # 清空标签统计表
        TagStatistics.objects.all().delete()
    
    def tearDown(self):
        """测试后清理"""
        # 清理测试数据
        PersonaCard.objects.all().delete()
        KnowledgeBase.objects.all().delete()
        TagStatistics.objects.all().delete()
        Users.objects.all().delete()
    
    def test_delete_public_persona_card_should_decrease_tag_usage(self):
        """测试删除公开 PersonaCard 时应减少标签统计
        
        **Bug Condition 1.1**: 删除公开内容时，系统不会减少对应标签的 usage_count
        
        **Expected Behavior**: 删除公开内容时，应减少标签的 usage_count，
        如果 usage_count 降为 0，应删除 TagStatistics 记录
        
        **Validates: Requirements 1.1, 2.1**
        """
        # 创建公开的 PersonaCard
        persona_card = PersonaCard.objects.create(
            name='测试人设卡',
            description='测试描述',
            uploader=self.user,
            tags=['AI', '助手'],
            is_public=True,
            is_pending=False
        )
        
        # 手动更新标签统计（模拟创建时的行为）
        TagService.update_tag_usage(['AI', '助手'], tag_type='persona')
        
        # 验证标签统计已创建
        ai_tag = TagStatistics.objects.get(tag='AI', tag_type='persona')
        helper_tag = TagStatistics.objects.get(tag='助手', tag_type='persona')
        self.assertEqual(ai_tag.usage_count, 1)
        self.assertEqual(helper_tag.usage_count, 1)
        
        # 软删除 PersonaCard
        persona_card.is_deleted = True
        persona_card.save()
        
        # **期望行为**：标签统计应该减少并删除记录
        # 断言：usage_count 为 0 的记录应该被删除
        self.assertFalse(
            TagStatistics.objects.filter(tag='AI', tag_type='persona').exists(),
            "删除公开 PersonaCard 后，'AI' 标签记录应该被删除"
        )
        self.assertFalse(
            TagStatistics.objects.filter(tag='助手', tag_type='persona').exists(),
            "删除公开 PersonaCard 后，'助手' 标签记录应该被删除"
        )
    
    def test_delete_public_knowledge_base_should_decrease_tag_usage(self):
        """测试删除公开 KnowledgeBase 时应减少标签统计
        
        **Bug Condition 1.1**: 删除公开内容时，系统不会减少对应标签的 usage_count
        
        **Expected Behavior**: 删除公开内容时，应减少标签的 usage_count
        
        **Validates: Requirements 1.1, 2.1**
        """
        # 创建公开的 KnowledgeBase
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='测试描述',
            uploader=self.user,
            tags=['Python', 'Django'],
            is_public=True,
            is_pending=False
        )
        
        # 手动更新标签统计
        TagService.update_tag_usage(['Python', 'Django'], tag_type='knowledge')
        
        # 验证标签统计已创建
        python_tag = TagStatistics.objects.get(tag='Python', tag_type='knowledge')
        django_tag = TagStatistics.objects.get(tag='Django', tag_type='knowledge')
        self.assertEqual(python_tag.usage_count, 1)
        self.assertEqual(django_tag.usage_count, 1)
        
        # 物理删除 KnowledgeBase
        kb.delete()
        
        # **期望行为**：标签统计应该减少并删除记录
        self.assertFalse(
            TagStatistics.objects.filter(tag='Python', tag_type='knowledge').exists(),
            "删除公开 KnowledgeBase 后，'Python' 标签记录应该被删除"
        )
        self.assertFalse(
            TagStatistics.objects.filter(tag='Django', tag_type='knowledge').exists(),
            "删除公开 KnowledgeBase 后，'Django' 标签记录应该被删除"
        )
    
    def test_public_to_private_should_decrease_tag_usage(self):
        """测试公开转私有时应减少标签统计
        
        **Bug Condition 1.2**: 将内容从公开改为私有时，系统不会减少对应标签的 usage_count
        
        **Expected Behavior**: 公开转私有时，应减少标签的 usage_count
        
        **Validates: Requirements 1.2, 2.2**
        """
        # 创建公开的 PersonaCard
        persona_card = PersonaCard.objects.create(
            name='测试人设卡',
            description='测试描述',
            uploader=self.user,
            tags=['游戏', '娱乐'],
            is_public=True,
            is_pending=False
        )
        
        # 手动更新标签统计
        TagService.update_tag_usage(['游戏', '娱乐'], tag_type='persona')
        
        # 验证标签统计已创建
        game_tag = TagStatistics.objects.get(tag='游戏', tag_type='persona')
        entertainment_tag = TagStatistics.objects.get(tag='娱乐', tag_type='persona')
        self.assertEqual(game_tag.usage_count, 1)
        self.assertEqual(entertainment_tag.usage_count, 1)
        
        # 将 PersonaCard 从公开改为私有
        persona_card.is_public = False
        persona_card.save()
        
        # **期望行为**：标签统计应该减少并删除记录
        # 断言：usage_count 为 0 的记录应该被删除
        self.assertFalse(
            TagStatistics.objects.filter(tag='游戏', tag_type='persona').exists(),
            "公开转私有后，'游戏' 标签记录应该被删除"
        )
        self.assertFalse(
            TagStatistics.objects.filter(tag='娱乐', tag_type='persona').exists(),
            "公开转私有后，'娱乐' 标签记录应该被删除"
        )
    
    def test_private_to_public_should_increase_tag_usage(self):
        """测试私有转公开时应增加标签统计
        
        **Bug Condition 1.3**: 将内容从私有改为公开时，系统不会增加对应标签的 usage_count
        
        **Expected Behavior**: 私有转公开时，应增加标签的 usage_count
        
        **Validates: Requirements 1.3, 2.3**
        """
        # 创建私有的 KnowledgeBase
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='测试描述',
            uploader=self.user,
            tags=['机器学习', '深度学习'],
            is_public=False,
            is_pending=True
        )
        
        # 验证标签统计不存在（因为是私有的）
        self.assertFalse(
            TagStatistics.objects.filter(tag='机器学习', tag_type='knowledge').exists()
        )
        self.assertFalse(
            TagStatistics.objects.filter(tag='深度学习', tag_type='knowledge').exists()
        )
        
        # 将 KnowledgeBase 从私有改为公开
        kb.is_public = True
        kb.is_pending = False
        kb.save()
        
        # **期望行为**：标签统计应该增加
        ml_tag = TagStatistics.objects.filter(tag='机器学习', tag_type='knowledge').first()
        dl_tag = TagStatistics.objects.filter(tag='深度学习', tag_type='knowledge').first()
        
        self.assertIsNotNone(ml_tag, "私有转公开后，'机器学习' 标签统计应该被创建")
        self.assertIsNotNone(dl_tag, "私有转公开后，'深度学习' 标签统计应该被创建")
        self.assertEqual(ml_tag.usage_count, 1, "'机器学习' 标签的 usage_count 应该为 1")
        self.assertEqual(dl_tag.usage_count, 1, "'深度学习' 标签的 usage_count 应该为 1")
    
    def test_update_tags_should_sync_statistics(self):
        """测试更新标签列表时应同步标签统计
        
        **Bug Condition 1.4**: 更新标签列表时，系统只增加新标签的 usage_count，
        不减少被删除标签的 usage_count
        
        **Expected Behavior**: 更新标签列表时，新增标签的 usage_count 应增加，
        删除标签的 usage_count 应减少
        
        **Validates: Requirements 1.4, 2.4**
        """
        # 创建公开的 KnowledgeBase
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='测试描述',
            uploader=self.user,
            tags=['Python', 'Django'],
            is_public=True,
            is_pending=False
        )
        
        # 手动更新标签统计
        TagService.update_tag_usage(['Python', 'Django'], tag_type='knowledge')
        
        # 验证标签统计已创建
        python_tag = TagStatistics.objects.get(tag='Python', tag_type='knowledge')
        django_tag = TagStatistics.objects.get(tag='Django', tag_type='knowledge')
        self.assertEqual(python_tag.usage_count, 1)
        self.assertEqual(django_tag.usage_count, 1)
        
        # 更新标签列表：删除 'Django'，添加 'FastAPI'，保留 'Python'
        kb.tags = ['Python', 'FastAPI']
        kb.save()
        
        # **期望行为**：
        # - 'Python' 的 usage_count 应保持不变（仍为 1）
        # - 'Django' 的 usage_count 应减少到 0 并删除记录
        # - 'FastAPI' 的 usage_count 应增加到 1
        
        python_tag.refresh_from_db()
        self.assertEqual(
            python_tag.usage_count, 1,
            "'Python' 标签的 usage_count 应保持为 1"
        )
        
        # 'Django' 标签应该被删除
        self.assertFalse(
            TagStatistics.objects.filter(tag='Django', tag_type='knowledge').exists(),
            "删除的 'Django' 标签记录应该被删除"
        )
        
        # 'FastAPI' 标签应该被创建
        fastapi_tag = TagStatistics.objects.filter(tag='FastAPI', tag_type='knowledge').first()
        self.assertIsNotNone(fastapi_tag, "新增的 'FastAPI' 标签统计应该被创建")
        self.assertEqual(fastapi_tag.usage_count, 1, "'FastAPI' 标签的 usage_count 应该为 1")
    
    def test_zombie_tags_should_not_exist(self):
        """测试不应存在僵尸标签（usage_count > 0 但无对应公开内容）
        
        **Bug Condition 1.5**: TagStatistics 表中存在 usage_count > 0 但实际没有
        对应公开内容的记录，这些"僵尸记录"会持续显示在热门标签列表中
        
        **Expected Behavior**: 查询热门标签时，应只返回 usage_count > 0 且
        对应有实际公开内容的标签
        
        **Validates: Requirements 1.5, 2.5**
        """
        # 创建公开的 PersonaCard
        persona_card = PersonaCard.objects.create(
            name='测试人设卡',
            description='测试描述',
            uploader=self.user,
            tags=['稀有标签'],
            is_public=True,
            is_pending=False
        )
        
        # 手动更新标签统计
        TagService.update_tag_usage(['稀有标签'], tag_type='persona')
        
        # 验证标签统计已创建
        rare_tag = TagStatistics.objects.get(tag='稀有标签', tag_type='persona')
        self.assertEqual(rare_tag.usage_count, 1)
        
        # 删除 PersonaCard
        persona_card.is_deleted = True
        persona_card.save()
        
        # **期望行为**：标签统计应该被删除，不应存在僵尸记录
        self.assertFalse(
            TagStatistics.objects.filter(tag='稀有标签', tag_type='persona').exists(),
            "删除唯一使用该标签的内容后，标签记录应该被删除，不应存在僵尸记录"
        )
        
        # 验证热门标签列表不包含僵尸标签
        popular_tags = TagService.get_popular_tags(limit=20, tag_type='persona')
        tag_names = [tag['tag'] for tag in popular_tags]
        self.assertNotIn(
            '稀有标签', tag_names,
            "热门标签列表不应包含已删除内容的标签"
        )
    
    def test_multiple_contents_share_same_tag(self):
        """测试多个内容共享同一标签时的统计同步
        
        **Bug Condition**: 当多个内容使用同一标签时，删除其中一个内容应该
        正确减少 usage_count，但不应删除标签记录（因为还有其他内容在使用）
        
        **Expected Behavior**: 删除一个内容时，usage_count 应减 1，
        但标签记录应保留（因为 usage_count > 0）
        
        **Validates: Requirements 1.1, 2.1**
        """
        # 创建两个公开的 PersonaCard，都使用 'AI' 标签
        persona_card1 = PersonaCard.objects.create(
            name='测试人设卡1',
            description='测试描述1',
            uploader=self.user,
            tags=['AI', '助手'],
            is_public=True,
            is_pending=False
        )
        
        persona_card2 = PersonaCard.objects.create(
            name='测试人设卡2',
            description='测试描述2',
            uploader=self.user,
            tags=['AI', '聊天'],
            is_public=True,
            is_pending=False
        )
        
        # 手动更新标签统计
        TagService.update_tag_usage(['AI', '助手'], tag_type='persona')
        TagService.update_tag_usage(['AI', '聊天'], tag_type='persona')
        
        # 验证 'AI' 标签的 usage_count 为 2
        ai_tag = TagStatistics.objects.get(tag='AI', tag_type='persona')
        self.assertEqual(ai_tag.usage_count, 2)
        
        # 删除第一个 PersonaCard
        persona_card1.is_deleted = True
        persona_card1.save()
        
        # **期望行为**：'AI' 标签的 usage_count 应减少到 1，但记录应保留
        ai_tag.refresh_from_db()
        self.assertEqual(
            ai_tag.usage_count, 1,
            "删除一个使用 'AI' 标签的内容后，usage_count 应减少到 1"
        )
        
        # 验证 'AI' 标签记录仍然存在
        self.assertTrue(
            TagStatistics.objects.filter(tag='AI', tag_type='persona').exists(),
            "'AI' 标签记录应该保留（因为还有其他内容在使用）"
        )
        
        # 验证 '助手' 标签应该被删除（只有一个内容使用）
        self.assertFalse(
            TagStatistics.objects.filter(tag='助手', tag_type='persona').exists(),
            "'助手' 标签记录应该被删除（只有一个内容使用，且已删除）"
        )
        
        # 验证 '聊天' 标签应该保留
        chat_tag = TagStatistics.objects.get(tag='聊天', tag_type='persona')
        self.assertEqual(chat_tag.usage_count, 1)


class TagStatisticsLifecycleScopedPropertyTest(HypothesisTestCase):
    """标签统计生命周期作用域属性测试
    
    使用作用域 PBT 方法，针对确定性 bug 生成具体的失败案例。
    
    **Validates: Requirements 1.1, 1.2, 1.3, 1.4**
    """
    
    def setUp(self):
        """测试前准备"""
        # 创建测试用户（如果已存在则获取）
        self.user, _ = Users.objects.get_or_create(
            username='testuser_pbt',
            defaults={
                'email': 'test_pbt@example.com',
                'name': '测试用户PBT'
            }
        )
        TagStatistics.objects.all().delete()
    
    def tearDown(self):
        """测试后清理"""
        PersonaCard.objects.all().delete()
        KnowledgeBase.objects.all().delete()
        TagStatistics.objects.all().delete()
        Users.objects.all().delete()
    
    @given(
        tags=st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
                min_size=1,
                max_size=10
            ),
            min_size=1,
            max_size=5,
            unique=True
        )
    )
    @settings(max_examples=5, deadline=None)
    def test_delete_operation_should_sync_tags(self, tags):
        """属性测试：删除操作应同步标签统计
        
        **Property**: 对于任何标签列表，删除公开内容后，标签统计应正确减少
        
        **Validates: Requirements 1.1, 2.1**
        """
        # 创建公开的 PersonaCard
        persona_card = PersonaCard.objects.create(
            name='测试人设卡',
            description='测试描述',
            uploader=self.user,
            tags=tags,
            is_public=True,
            is_pending=False
        )
        
        # 手动更新标签统计
        TagService.update_tag_usage(tags, tag_type='persona')
        
        # 验证标签统计已创建
        for tag in tags:
            tag_stat = TagStatistics.objects.get(tag=tag, tag_type='persona')
            self.assertEqual(tag_stat.usage_count, 1)
        
        # 删除 PersonaCard
        persona_card.is_deleted = True
        persona_card.save()
        
        # **期望行为**：所有标签的统计应该被删除
        for tag in tags:
            self.assertFalse(
                TagStatistics.objects.filter(tag=tag, tag_type='persona').exists(),
                f"删除内容后，标签 '{tag}' 的记录应该被删除"
            )
    
    @given(
        old_tags=st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
                min_size=1,
                max_size=10
            ),
            min_size=1,
            max_size=3,
            unique=True
        ),
        new_tags=st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
                min_size=1,
                max_size=10
            ),
            min_size=1,
            max_size=3,
            unique=True
        )
    )
    @settings(max_examples=5, deadline=None)
    def test_update_tags_should_sync_statistics_property(self, old_tags, new_tags):
        """属性测试：更新标签应同步统计
        
        **Property**: 对于任何旧标签列表和新标签列表，更新后标签统计应正确反映变化
        
        **Validates: Requirements 1.4, 2.4**
        """
        # 创建公开的 KnowledgeBase
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='测试描述',
            uploader=self.user,
            tags=old_tags,
            is_public=True,
            is_pending=False
        )
        
        # 手动更新标签统计
        TagService.update_tag_usage(old_tags, tag_type='knowledge')
        
        # 更新标签列表
        kb.tags = new_tags
        kb.save()
        
        # **期望行为**：
        # - 保留的标签：usage_count 应保持为 1
        # - 删除的标签：应该被删除
        # - 新增的标签：usage_count 应为 1
        
        old_tags_set = set(old_tags)
        new_tags_set = set(new_tags)
        
        kept_tags = old_tags_set & new_tags_set
        removed_tags = old_tags_set - new_tags_set
        added_tags = new_tags_set - old_tags_set
        
        # 验证保留的标签
        for tag in kept_tags:
            tag_stat = TagStatistics.objects.filter(tag=tag, tag_type='knowledge').first()
            self.assertIsNotNone(tag_stat, f"保留的标签 '{tag}' 应该存在")
            self.assertEqual(tag_stat.usage_count, 1, f"保留的标签 '{tag}' 的 usage_count 应为 1")
        
        # 验证删除的标签
        for tag in removed_tags:
            self.assertFalse(
                TagStatistics.objects.filter(tag=tag, tag_type='knowledge').exists(),
                f"删除的标签 '{tag}' 应该被删除"
            )
        
        # 验证新增的标签
        for tag in added_tags:
            tag_stat = TagStatistics.objects.filter(tag=tag, tag_type='knowledge').first()
            self.assertIsNotNone(tag_stat, f"新增的标签 '{tag}' 应该被创建")
            self.assertEqual(tag_stat.usage_count, 1, f"新增的标签 '{tag}' 的 usage_count 应为 1")

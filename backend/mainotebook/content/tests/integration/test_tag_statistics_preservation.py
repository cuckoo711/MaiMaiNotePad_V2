# -*- coding: utf-8 -*-

"""
标签统计保持不变属性测试

此测试文件验证现有功能在修复后保持不变。
测试在未修复的代码上运行，预期会通过，确认基线行为。

**重要提示**：
- 这些测试验证不受 bug 影响的功能
- 在未修复的代码上运行时应该通过
- 通过确认了要保持的基线行为
- 在实现修复后，这些测试应该继续通过（无回归）

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
"""

from django.test import TestCase
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase

from mainotebook.system.models import Users
from mainotebook.content.models import PersonaCard, KnowledgeBase, TagStatistics
from mainotebook.content.services.tag_service import TagService


# 配置 Hypothesis
settings.register_profile("preservation", max_examples=20, deadline=None)
settings.load_profile("preservation")


class TagStatisticsPreservationTest(TestCase):
    """标签统计保持不变属性测试
    
    **Property 2: Preservation** - 现有功能保持不变
    
    此测试类验证不受 bug 影响的功能在修复后继续正常工作。
    
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
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
        
        # 清空标签统计表
        TagStatistics.objects.all().delete()
    
    def tearDown(self):
        """测试后清理"""
        # 清理测试数据
        PersonaCard.objects.all().delete()
        KnowledgeBase.objects.all().delete()
        TagStatistics.objects.all().delete()
        Users.objects.all().delete()
    
    def test_create_public_content_increases_tag_usage(self):
        """测试创建公开内容时增加标签统计
        
        **Preservation Behavior 3.1**: 创建新的公开 PersonaCard 或 KnowledgeBase 时，
        系统应继续增加对应标签的 usage_count（现有功能正常）
        
        **Validates: Requirements 3.1**
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
        
        # 手动调用标签统计更新（模拟 perform_create 中的行为）
        TagService.update_tag_usage(['AI', '助手'], tag_type='persona')
        
        # 验证标签统计已创建
        ai_tag = TagStatistics.objects.get(tag='AI', tag_type='persona')
        helper_tag = TagStatistics.objects.get(tag='助手', tag_type='persona')
        
        self.assertEqual(ai_tag.usage_count, 1, "'AI' 标签的 usage_count 应该为 1")
        self.assertEqual(helper_tag.usage_count, 1, "'助手' 标签的 usage_count 应该为 1")
        
        # 创建另一个公开的 KnowledgeBase
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='测试描述',
            uploader=self.user,
            tags=['Python', 'Django'],
            is_public=True,
            is_pending=False
        )
        
        # 手动调用标签统计更新
        TagService.update_tag_usage(['Python', 'Django'], tag_type='knowledge')
        
        # 验证标签统计已创建
        python_tag = TagStatistics.objects.get(tag='Python', tag_type='knowledge')
        django_tag = TagStatistics.objects.get(tag='Django', tag_type='knowledge')
        
        self.assertEqual(python_tag.usage_count, 1, "'Python' 标签的 usage_count 应该为 1")
        self.assertEqual(django_tag.usage_count, 1, "'Django' 标签的 usage_count 应该为 1")
    
    def test_rebuild_statistics_works_correctly(self):
        """测试重建统计功能
        
        **Preservation Behavior 3.2**: 调用 TagService.rebuild_statistics() 时，
        系统应继续从零重建所有标签统计，只统计 is_public=True 的内容
        
        注意：当前实现未过滤 is_deleted 字段，这是已知的 bug，但这里测试的是保持不变的行为
        
        **Validates: Requirements 3.2**
        """
        # 创建多个内容
        # 公开的 PersonaCard
        PersonaCard.objects.create(
            name='公开人设卡1',
            description='测试描述',
            uploader=self.user,
            tags=['AI', '助手'],
            is_public=True,
            is_pending=False,
            is_deleted=False
        )
        
        # 私有的 PersonaCard（不应计入统计）
        PersonaCard.objects.create(
            name='私有人设卡',
            description='测试描述',
            uploader=self.user,
            tags=['私有标签'],
            is_public=False,
            is_pending=True,
            is_deleted=False
        )
        
        # 公开的 KnowledgeBase
        KnowledgeBase.objects.create(
            name='公开知识库1',
            description='测试描述',
            uploader=self.user,
            tags=['Python', 'Django'],
            is_public=True,
            is_pending=False
        )
        
        # 私有的 KnowledgeBase（不应计入统计）
        KnowledgeBase.objects.create(
            name='私有知识库',
            description='测试描述',
            uploader=self.user,
            tags=['私有知识'],
            is_public=False,
            is_pending=True
        )
        
        # 调用重建统计
        result = TagService.rebuild_statistics()
        
        # 验证统计结果
        self.assertEqual(result['persona_tags'], 2, "应该有 2 个 persona 标签")
        self.assertEqual(result['knowledge_tags'], 2, "应该有 2 个 knowledge 标签")
        
        # 验证公开内容的标签统计
        ai_tag = TagStatistics.objects.get(tag='AI', tag_type='persona')
        helper_tag = TagStatistics.objects.get(tag='助手', tag_type='persona')
        python_tag = TagStatistics.objects.get(tag='Python', tag_type='knowledge')
        django_tag = TagStatistics.objects.get(tag='Django', tag_type='knowledge')
        
        self.assertEqual(ai_tag.usage_count, 1)
        self.assertEqual(helper_tag.usage_count, 1)
        self.assertEqual(python_tag.usage_count, 1)
        self.assertEqual(django_tag.usage_count, 1)
        
        # 验证私有内容的标签不存在
        self.assertFalse(
            TagStatistics.objects.filter(tag='私有标签', tag_type='persona').exists(),
            "私有内容的标签不应计入统计"
        )
        self.assertFalse(
            TagStatistics.objects.filter(tag='私有知识', tag_type='knowledge').exists(),
            "私有内容的标签不应计入统计"
        )
    
    def test_update_non_tag_fields_does_not_affect_statistics(self):
        """测试更新非标签字段不影响标签统计
        
        **Preservation Behavior 3.3**: 更新 PersonaCard 或 KnowledgeBase 的非标签字段
        （如 name、description）时，系统应继续不影响标签统计
        
        **Validates: Requirements 3.3**
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
        
        # 手动调用标签统计更新
        TagService.update_tag_usage(['AI', '助手'], tag_type='persona')
        
        # 记录初始的 usage_count
        ai_tag = TagStatistics.objects.get(tag='AI', tag_type='persona')
        helper_tag = TagStatistics.objects.get(tag='助手', tag_type='persona')
        initial_ai_count = ai_tag.usage_count
        initial_helper_count = helper_tag.usage_count
        
        # 更新非标签字段
        persona_card.name = '更新后的名称'
        persona_card.description = '更新后的描述'
        persona_card.save()
        
        # 验证标签统计未变化
        ai_tag.refresh_from_db()
        helper_tag.refresh_from_db()
        
        self.assertEqual(
            ai_tag.usage_count, initial_ai_count,
            "更新非标签字段后，'AI' 标签的 usage_count 应保持不变"
        )
        self.assertEqual(
            helper_tag.usage_count, initial_helper_count,
            "更新非标签字段后，'助手' 标签的 usage_count 应保持不变"
        )
        
        # 创建公开的 KnowledgeBase
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='测试描述',
            uploader=self.user,
            tags=['Python', 'Django'],
            is_public=True,
            is_pending=False
        )
        
        # 手动调用标签统计更新
        TagService.update_tag_usage(['Python', 'Django'], tag_type='knowledge')
        
        # 记录初始的 usage_count
        python_tag = TagStatistics.objects.get(tag='Python', tag_type='knowledge')
        django_tag = TagStatistics.objects.get(tag='Django', tag_type='knowledge')
        initial_python_count = python_tag.usage_count
        initial_django_count = django_tag.usage_count
        
        # 更新非标签字段
        kb.name = '更新后的知识库名称'
        kb.description = '更新后的知识库描述'
        kb.save()
        
        # 验证标签统计未变化
        python_tag.refresh_from_db()
        django_tag.refresh_from_db()
        
        self.assertEqual(
            python_tag.usage_count, initial_python_count,
            "更新非标签字段后，'Python' 标签的 usage_count 应保持不变"
        )
        self.assertEqual(
            django_tag.usage_count, initial_django_count,
            "更新非标签字段后，'Django' 标签的 usage_count 应保持不变"
        )
    
    def test_query_tags_ordered_by_usage_count(self):
        """测试查询标签统计按 usage_count 降序返回
        
        **Preservation Behavior 3.4**: 查询标签统计时，系统应继续按 usage_count 降序返回结果
        
        **Validates: Requirements 3.4**
        """
        # 创建多个内容，使用不同的标签
        # 'AI' 标签使用 3 次
        for i in range(3):
            PersonaCard.objects.create(
                name=f'人设卡{i}',
                description='测试描述',
                uploader=self.user,
                tags=['AI'],
                is_public=True,
                is_pending=False
            )
            TagService.update_tag_usage(['AI'], tag_type='persona')
        
        # '助手' 标签使用 2 次
        for i in range(2):
            PersonaCard.objects.create(
                name=f'助手人设卡{i}',
                description='测试描述',
                uploader=self.user,
                tags=['助手'],
                is_public=True,
                is_pending=False
            )
            TagService.update_tag_usage(['助手'], tag_type='persona')
        
        # '聊天' 标签使用 1 次
        PersonaCard.objects.create(
            name='聊天人设卡',
            description='测试描述',
            uploader=self.user,
            tags=['聊天'],
            is_public=True,
            is_pending=False
        )
        TagService.update_tag_usage(['聊天'], tag_type='persona')
        
        # 查询热门标签
        popular_tags = TagService.get_popular_tags(limit=10, tag_type='persona')
        
        # 验证返回的标签按 usage_count 降序排列
        self.assertEqual(len(popular_tags), 3, "应该返回 3 个标签")
        self.assertEqual(popular_tags[0]['tag'], 'AI', "第一个标签应该是 'AI'")
        self.assertEqual(popular_tags[0]['usage_count'], 3, "'AI' 的 usage_count 应该是 3")
        self.assertEqual(popular_tags[1]['tag'], '助手', "第二个标签应该是 '助手'")
        self.assertEqual(popular_tags[1]['usage_count'], 2, "'助手' 的 usage_count 应该是 2")
        self.assertEqual(popular_tags[2]['tag'], '聊天', "第三个标签应该是 '聊天'")
        self.assertEqual(popular_tags[2]['usage_count'], 1, "'聊天' 的 usage_count 应该是 1")
        
        # 验证 usage_count 是降序的
        for i in range(len(popular_tags) - 1):
            self.assertGreaterEqual(
                popular_tags[i]['usage_count'],
                popular_tags[i + 1]['usage_count'],
                "标签应该按 usage_count 降序排列"
            )
    
    def test_private_content_tags_not_counted(self):
        """测试操作私有内容的标签不计入公开标签统计
        
        **Preservation Behavior 3.5**: 操作私有内容（is_public=False）的标签时，
        系统应继续不将这些标签计入公开标签统计
        
        **Validates: Requirements 3.5**
        """
        # 创建私有的 PersonaCard
        private_persona = PersonaCard.objects.create(
            name='私有人设卡',
            description='测试描述',
            uploader=self.user,
            tags=['私有标签1', '私有标签2'],
            is_public=False,
            is_pending=True
        )
        
        # 验证私有内容的标签不存在于统计中
        self.assertFalse(
            TagStatistics.objects.filter(tag='私有标签1', tag_type='persona').exists(),
            "私有内容的标签不应计入公开标签统计"
        )
        self.assertFalse(
            TagStatistics.objects.filter(tag='私有标签2', tag_type='persona').exists(),
            "私有内容的标签不应计入公开标签统计"
        )
        
        # 创建私有的 KnowledgeBase
        private_kb = KnowledgeBase.objects.create(
            name='私有知识库',
            description='测试描述',
            uploader=self.user,
            tags=['私有知识1', '私有知识2'],
            is_public=False,
            is_pending=True
        )
        
        # 验证私有内容的标签不存在于统计中
        self.assertFalse(
            TagStatistics.objects.filter(tag='私有知识1', tag_type='knowledge').exists(),
            "私有内容的标签不应计入公开标签统计"
        )
        self.assertFalse(
            TagStatistics.objects.filter(tag='私有知识2', tag_type='knowledge').exists(),
            "私有内容的标签不应计入公开标签统计"
        )
        
        # 更新私有内容的标签
        private_persona.tags = ['新私有标签']
        private_persona.save()
        
        # 验证新的私有标签也不存在于统计中
        self.assertFalse(
            TagStatistics.objects.filter(tag='新私有标签', tag_type='persona').exists(),
            "更新后的私有内容标签不应计入公开标签统计"
        )
        
        # 查询热门标签，验证不包含私有标签
        popular_persona_tags = TagService.get_popular_tags(limit=20, tag_type='persona')
        popular_knowledge_tags = TagService.get_popular_tags(limit=20, tag_type='knowledge')
        
        persona_tag_names = [tag['tag'] for tag in popular_persona_tags]
        knowledge_tag_names = [tag['tag'] for tag in popular_knowledge_tags]
        
        self.assertNotIn('私有标签1', persona_tag_names, "热门标签不应包含私有标签")
        self.assertNotIn('私有标签2', persona_tag_names, "热门标签不应包含私有标签")
        self.assertNotIn('新私有标签', persona_tag_names, "热门标签不应包含私有标签")
        self.assertNotIn('私有知识1', knowledge_tag_names, "热门标签不应包含私有标签")
        self.assertNotIn('私有知识2', knowledge_tag_names, "热门标签不应包含私有标签")


class TagStatisticsPreservationPropertyTest(HypothesisTestCase):
    """标签统计保持不变基于属性的测试
    
    使用 Hypothesis 生成大量测试用例，验证保持不变的行为在各种输入下都正确。
    
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
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
    @settings(max_examples=10, deadline=None)
    def test_create_public_content_property(self, tags):
        """属性测试：创建公开内容时增加标签统计
        
        **Property**: 对于任何标签列表，创建公开内容后，标签统计应正确增加
        
        **Validates: Requirements 3.1**
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
        
        # 手动调用标签统计更新
        TagService.update_tag_usage(tags, tag_type='persona')
        
        # 验证所有标签的统计都已创建
        for tag in tags:
            tag_stat = TagStatistics.objects.filter(tag=tag, tag_type='persona').first()
            self.assertIsNotNone(tag_stat, f"标签 '{tag}' 的统计应该被创建")
            self.assertGreaterEqual(tag_stat.usage_count, 1, f"标签 '{tag}' 的 usage_count 应该 >= 1")
    
    @given(
        name=st.text(
            alphabet=st.characters(
                blacklist_characters='\x00',  # 排除 NUL 字符
                blacklist_categories=('Cs',)  # 排除代理字符
            ),
            min_size=1,
            max_size=50
        ),
        description=st.text(
            alphabet=st.characters(
                blacklist_characters='\x00',  # 排除 NUL 字符
                blacklist_categories=('Cs',)  # 排除代理字符
            ),
            min_size=1,
            max_size=200
        )
    )
    @settings(max_examples=10, deadline=None)
    def test_update_non_tag_fields_property(self, name, description):
        """属性测试：更新非标签字段不影响标签统计
        
        **Property**: 对于任何 name 和 description 值，更新这些字段不应影响标签统计
        
        **Validates: Requirements 3.3**
        """
        # 创建公开的 PersonaCard
        persona_card = PersonaCard.objects.create(
            name='初始名称',
            description='初始描述',
            uploader=self.user,
            tags=['测试标签'],
            is_public=True,
            is_pending=False
        )
        
        # 手动调用标签统计更新
        TagService.update_tag_usage(['测试标签'], tag_type='persona')
        
        # 记录初始的 usage_count
        tag_stat = TagStatistics.objects.get(tag='测试标签', tag_type='persona')
        initial_count = tag_stat.usage_count
        
        # 更新非标签字段
        persona_card.name = name
        persona_card.description = description
        persona_card.save()
        
        # 验证标签统计未变化
        tag_stat.refresh_from_db()
        self.assertEqual(
            tag_stat.usage_count, initial_count,
            f"更新 name='{name}', description='{description}' 后，标签统计应保持不变"
        )
    
    @given(
        is_public=st.booleans()
    )
    @settings(max_examples=10, deadline=None)
    def test_private_content_not_counted_property(self, is_public):
        """属性测试：私有内容的标签不计入统计
        
        **Property**: 对于任何 is_public 值，只有 is_public=True 的内容标签才计入统计
        
        **Validates: Requirements 3.5**
        """
        # 创建内容
        persona_card = PersonaCard.objects.create(
            name='测试人设卡',
            description='测试描述',
            uploader=self.user,
            tags=['测试标签'],
            is_public=is_public,
            is_pending=not is_public
        )
        
        # 如果是公开的，手动调用标签统计更新（模拟 perform_create 行为）
        if is_public:
            TagService.update_tag_usage(['测试标签'], tag_type='persona')
        
        # 验证标签统计
        tag_exists = TagStatistics.objects.filter(tag='测试标签', tag_type='persona').exists()
        
        if is_public:
            self.assertTrue(tag_exists, "公开内容的标签应该存在于统计中")
        else:
            self.assertFalse(tag_exists, "私有内容的标签不应该存在于统计中")

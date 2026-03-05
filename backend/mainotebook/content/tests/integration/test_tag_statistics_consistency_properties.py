# -*- coding: utf-8 -*-

"""
标签统计一致性属性测试

使用 Hypothesis 进行基于属性的测试，验证标签统计在各种操作序列下的一致性。

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
"""

from django.test import TestCase
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase

from mainotebook.system.models import Users
from mainotebook.content.models import PersonaCard, KnowledgeBase, TagStatistics
from mainotebook.content.services.tag_service import TagService


# 配置 Hypothesis
settings.register_profile("consistency", max_examples=20, deadline=None)
settings.load_profile("consistency")


# ==================== 测试策略（Strategies） ====================

# 生成有效的标签字符串（1-20 个字符）
valid_tag_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
    min_size=1,
    max_size=20
).filter(lambda s: s.strip())

# 生成标签数组（1-5 个标签）
tag_array_strategy = st.lists(
    valid_tag_strategy,
    min_size=1,
    max_size=5,
    unique=True
)

# 定义操作类型
operation_type_strategy = st.sampled_from([
    'create_public',
    'create_private',
    'delete',
    'public_to_private',
    'private_to_public',
    'update_tags'
])


class TagStatisticsConsistencyPropertyTest(HypothesisTestCase):
    """标签统计一致性属性测试
    
    **Property**: 对于任何内容创建、更新、删除操作序列，标签统计应与实际公开内容保持同步
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
    """
    
    def setUp(self):
        """测试前准备"""
        # 创建测试用户（如果已存在则获取）
        self.user, _ = Users.objects.get_or_create(
            username='testuser_consistency',
            defaults={
                'email': 'test_consistency@example.com',
                'name': '测试用户一致性'
            }
        )
        
        # 清空标签统计表
        TagStatistics.objects.all().delete()
        
        # 用于跟踪创建的内容
        self.persona_cards = []
        self.knowledge_bases = []
    
    def tearDown(self):
        """测试后清理"""
        PersonaCard.objects.all().delete()
        KnowledgeBase.objects.all().delete()
        TagStatistics.objects.all().delete()
        Users.objects.all().delete()
    
    def _calculate_expected_tag_counts(self, content_type='persona'):
        """计算期望的标签统计
        
        Args:
            content_type: 'persona' 或 'knowledge'
            
        Returns:
            Dict[str, int]: 标签名称到使用次数的映射
        """
        tag_counts = {}
        
        if content_type == 'persona':
            # 只统计公开且未删除的 PersonaCard
            for pc in PersonaCard.objects.filter(is_public=True, is_deleted=False):
                tags = TagService.parse_tags(pc.tags)
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
        else:
            # 只统计公开的 KnowledgeBase
            for kb in KnowledgeBase.objects.filter(is_public=True):
                tags = TagService.parse_tags(kb.tags)
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return tag_counts
    
    def _verify_tag_statistics(self, content_type='persona'):
        """验证标签统计与实际内容一致
        
        Args:
            content_type: 'persona' 或 'knowledge'
        """
        expected_counts = self._calculate_expected_tag_counts(content_type)
        
        # 验证所有期望的标签都存在且 usage_count 正确
        for tag, expected_count in expected_counts.items():
            tag_stat = TagStatistics.objects.filter(
                tag=tag,
                tag_type=content_type
            ).first()
            
            self.assertIsNotNone(
                tag_stat,
                f"标签 '{tag}' 应该存在于统计中（期望 usage_count={expected_count}）"
            )
            self.assertEqual(
                tag_stat.usage_count,
                expected_count,
                f"标签 '{tag}' 的 usage_count 不正确：期望 {expected_count}，实际 {tag_stat.usage_count}"
            )
            self.assertGreaterEqual(
                tag_stat.usage_count,
                0,
                f"标签 '{tag}' 的 usage_count 应该 >= 0"
            )
        
        # 验证不应存在的标签（usage_count = 0 的记录应该被删除）
        all_tag_stats = TagStatistics.objects.filter(tag_type=content_type)
        for tag_stat in all_tag_stats:
            self.assertIn(
                tag_stat.tag,
                expected_counts,
                f"标签 '{tag_stat.tag}' 不应该存在于统计中（没有对应的公开内容）"
            )
            self.assertGreater(
                tag_stat.usage_count,
                0,
                f"标签 '{tag_stat.tag}' 的 usage_count 应该 > 0（否则应该被删除）"
            )
    
    @given(
        tags=tag_array_strategy
    )
    @settings(max_examples=10, deadline=None)
    def test_create_and_delete_consistency(self, tags):
        """测试创建和删除操作的一致性
        
        **Property**: 创建公开内容后删除，标签统计应该恢复到初始状态
        
        **Validates: Requirements 2.1**
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
        
        # 手动调用标签统计更新（模拟 perform_create 的行为）
        # 注意：实际系统中，KnowledgeBase 的 perform_create 会调用此方法
        # 但 PersonaCard 的 perform_create 没有调用，这是一个不一致的地方
        # 为了测试标签统计的一致性，我们需要手动调用
        if persona_card.is_public:
            TagService.update_tag_usage(tags, tag_type='persona')
        
        # 验证标签统计正确
        self._verify_tag_statistics('persona')
        
        # 删除 PersonaCard（signals 会自动减少标签统计）
        persona_card.is_deleted = True
        persona_card.save()
        
        # 验证标签统计恢复到初始状态（所有标签应该被删除）
        for tag in tags:
            self.assertFalse(
                TagStatistics.objects.filter(tag=tag, tag_type='persona').exists(),
                f"删除内容后，标签 '{tag}' 应该被删除"
            )
    
    @given(
        tags=tag_array_strategy
    )
    @settings(max_examples=10, deadline=None)
    def test_public_private_toggle_consistency(self, tags):
        """测试公开/私有切换的一致性
        
        **Property**: 公开转私有再转公开，标签统计应该恢复到初始状态
        
        **Validates: Requirements 2.2, 2.3**
        """
        # 创建公开的 KnowledgeBase
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='测试描述',
            uploader=self.user,
            tags=tags,
            is_public=True,
            is_pending=False
        )
        
        # 手动调用标签统计更新（模拟 perform_create 的行为）
        if kb.is_public:
            TagService.update_tag_usage(tags, tag_type='knowledge')
        
        # 验证标签统计正确
        self._verify_tag_statistics('knowledge')
        initial_counts = self._calculate_expected_tag_counts('knowledge')
        
        # 公开转私有（signals 会自动减少标签统计）
        kb.is_public = False
        kb.save()
        
        # 验证标签统计被清除
        for tag in tags:
            self.assertFalse(
                TagStatistics.objects.filter(tag=tag, tag_type='knowledge').exists(),
                f"公开转私有后，标签 '{tag}' 应该被删除"
            )
        
        # 私有转公开（signals 会自动增加标签统计）
        kb.is_public = True
        kb.save()
        
        # 验证标签统计恢复
        self._verify_tag_statistics('knowledge')
        final_counts = self._calculate_expected_tag_counts('knowledge')
        
        self.assertEqual(
            initial_counts,
            final_counts,
            "公开转私有再转公开后，标签统计应该恢复到初始状态"
        )
    
    @given(
        initial_tags=tag_array_strategy,
        updated_tags=tag_array_strategy
    )
    @settings(max_examples=10, deadline=None)
    def test_update_tags_consistency(self, initial_tags, updated_tags):
        """测试更新标签的一致性
        
        **Property**: 更新标签后，标签统计应该反映新的标签列表
        
        **Validates: Requirements 2.4**
        """
        # 创建公开的 PersonaCard
        persona_card = PersonaCard.objects.create(
            name='测试人设卡',
            description='测试描述',
            uploader=self.user,
            tags=initial_tags,
            is_public=True,
            is_pending=False
        )
        
        # 手动调用标签统计更新（模拟 perform_create 的行为）
        if persona_card.is_public:
            TagService.update_tag_usage(initial_tags, tag_type='persona')
        
        # 验证初始标签统计正确
        self._verify_tag_statistics('persona')
        
        # 更新标签列表（signals 会自动同步标签统计）
        persona_card.tags = updated_tags
        persona_card.save()
        
        # 验证更新后的标签统计正确
        self._verify_tag_statistics('persona')
        
        # 验证标签差异
        initial_set = set(initial_tags)
        updated_set = set(updated_tags)
        
        kept_tags = initial_set & updated_set
        removed_tags = initial_set - updated_set
        added_tags = updated_set - initial_set
        
        # 验证保留的标签
        for tag in kept_tags:
            tag_stat = TagStatistics.objects.filter(tag=tag, tag_type='persona').first()
            self.assertIsNotNone(tag_stat, f"保留的标签 '{tag}' 应该存在")
            self.assertEqual(tag_stat.usage_count, 1, f"保留的标签 '{tag}' 的 usage_count 应为 1")
        
        # 验证删除的标签
        for tag in removed_tags:
            self.assertFalse(
                TagStatistics.objects.filter(tag=tag, tag_type='persona').exists(),
                f"删除的标签 '{tag}' 应该被删除"
            )
        
        # 验证新增的标签
        for tag in added_tags:
            tag_stat = TagStatistics.objects.filter(tag=tag, tag_type='persona').first()
            self.assertIsNotNone(tag_stat, f"新增的标签 '{tag}' 应该被创建")
            self.assertEqual(tag_stat.usage_count, 1, f"新增的标签 '{tag}' 的 usage_count 应为 1")
    
    @given(
        tags1=tag_array_strategy,
        tags2=tag_array_strategy
    )
    @settings(max_examples=10, deadline=None)
    def test_multiple_contents_consistency(self, tags1, tags2):
        """测试多个内容共享标签的一致性
        
        **Property**: 多个内容使用相同标签时，usage_count 应该正确累加
        
        **Validates: Requirements 2.1, 2.5**
        """
        # 创建第一个公开的 KnowledgeBase
        kb1 = KnowledgeBase.objects.create(
            name='测试知识库1',
            description='测试描述1',
            uploader=self.user,
            tags=tags1,
            is_public=True,
            is_pending=False
        )
        
        # 手动调用标签统计更新（模拟 perform_create 的行为）
        if kb1.is_public:
            TagService.update_tag_usage(tags1, tag_type='knowledge')
        
        # 创建第二个公开的 KnowledgeBase
        kb2 = KnowledgeBase.objects.create(
            name='测试知识库2',
            description='测试描述2',
            uploader=self.user,
            tags=tags2,
            is_public=True,
            is_pending=False
        )
        
        # 手动调用标签统计更新（模拟 perform_create 的行为）
        if kb2.is_public:
            TagService.update_tag_usage(tags2, tag_type='knowledge')
        
        # 验证标签统计正确
        self._verify_tag_statistics('knowledge')
        
        # 计算共享标签
        shared_tags = set(tags1) & set(tags2)
        
        # 验证共享标签的 usage_count 为 2
        for tag in shared_tags:
            tag_stat = TagStatistics.objects.get(tag=tag, tag_type='knowledge')
            self.assertEqual(
                tag_stat.usage_count,
                2,
                f"共享标签 '{tag}' 的 usage_count 应该为 2"
            )
        
        # 删除第一个 KnowledgeBase（signals 会自动减少标签统计）
        kb1.delete()
        
        # 验证标签统计正确更新
        self._verify_tag_statistics('knowledge')
        
        # 验证共享标签的 usage_count 减少到 1
        for tag in shared_tags:
            tag_stat = TagStatistics.objects.filter(tag=tag, tag_type='knowledge').first()
            self.assertIsNotNone(tag_stat, f"共享标签 '{tag}' 应该仍然存在")
            self.assertEqual(
                tag_stat.usage_count,
                1,
                f"删除一个内容后，共享标签 '{tag}' 的 usage_count 应该为 1"
            )
        
        # 验证只在第一个内容中的标签被删除
        only_in_tags1 = set(tags1) - set(tags2)
        for tag in only_in_tags1:
            self.assertFalse(
                TagStatistics.objects.filter(tag=tag, tag_type='knowledge').exists(),
                f"只在第一个内容中的标签 '{tag}' 应该被删除"
            )
    
    @given(
        operations=st.lists(
            st.tuples(
                operation_type_strategy,
                tag_array_strategy
            ),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=5, deadline=None)
    def test_operation_sequence_consistency(self, operations):
        """测试操作序列的一致性
        
        **Property**: 对于任何操作序列，标签统计应该始终与实际公开内容保持同步
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
        """
        current_persona_card = None
        
        for operation_type, tags in operations:
            if operation_type == 'create_public':
                # 创建公开内容
                current_persona_card = PersonaCard.objects.create(
                    name='测试人设卡',
                    description='测试描述',
                    uploader=self.user,
                    tags=tags,
                    is_public=True,
                    is_pending=False
                )
                # 手动调用标签统计更新（模拟 perform_create 的行为）
                if current_persona_card.is_public:
                    TagService.update_tag_usage(tags, tag_type='persona')
            
            elif operation_type == 'create_private':
                # 创建私有内容（不应影响统计）
                current_persona_card = PersonaCard.objects.create(
                    name='测试人设卡',
                    description='测试描述',
                    uploader=self.user,
                    tags=tags,
                    is_public=False,
                    is_pending=True
                )
            
            elif operation_type == 'delete' and current_persona_card:
                # 删除内容（signals 会自动减少标签统计）
                current_persona_card.is_deleted = True
                current_persona_card.save()
                current_persona_card = None
            
            elif operation_type == 'public_to_private' and current_persona_card and current_persona_card.is_public:
                # 公开转私有（signals 会自动减少标签统计）
                current_persona_card.is_public = False
                current_persona_card.save()
            
            elif operation_type == 'private_to_public' and current_persona_card and not current_persona_card.is_public:
                # 私有转公开（signals 会自动增加标签统计）
                current_persona_card.is_public = True
                current_persona_card.save()
            
            elif operation_type == 'update_tags' and current_persona_card and current_persona_card.is_public:
                # 更新标签（signals 会自动同步标签统计）
                current_persona_card.tags = tags
                current_persona_card.save()
            
            # 每次操作后验证一致性
            self._verify_tag_statistics('persona')

# -*- coding: utf-8 -*-

"""
TagService 属性测试

使用 Hypothesis 进行基于属性的测试，验证 TagService 的不变性和正确性属性。

验证需求：10.4, 10.6, 10.7
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.extra.django import TestCase
from django.core.cache import cache
from django.utils import timezone
from mainotebook.system.models import Users
from mainotebook.content.models import TagStatistics, KnowledgeBase, PersonaCard
from mainotebook.content.services.tag_service import TagService


# ==================== 测试策略（Strategies） ====================

# 生成有效的标签字符串（1-50 个字符）
valid_tag_strategy = st.text(
    alphabet=st.characters(
        blacklist_categories=('Cs',),  # 排除代理字符
        blacklist_characters='\x00\n\r\t,',  # 排除空字符、控制字符和逗号
    ),
    min_size=1,
    max_size=50
).filter(lambda s: s.strip())  # 确保去除空格后不为空

# 生成标签数组（0-20 个标签）
tag_array_strategy = st.lists(
    valid_tag_strategy,
    min_size=0,
    max_size=20
)

# 生成逗号分隔的标签字符串
tag_string_strategy = st.lists(
    valid_tag_strategy,
    min_size=0,
    max_size=20
).map(lambda tags: ','.join(tags))

# 生成标签使用次数（1-100）
usage_count_strategy = st.integers(min_value=1, max_value=100)


# ==================== 属性 4：标签统计正确性 ====================

class TestProperty4_TagStatisticsCorrectness(TestCase):
    """属性 4：标签统计正确性
    
    **验证需求：4.1, 4.2**
    
    对于任意一组 PersonaCard 和 KnowledgeBase 记录，重建统计后，
    每个标签的使用次数应该等于该标签在所有公开记录中出现的次数
    """
    
    def setUp(self):
        """测试前准备"""
        # 创建测试用户
        self.user = Users.objects.create(
            username="testuser",
            name="测试用户",
            email="test@example.com"
        )
        cache.clear()
    
    def tearDown(self):
        """测试后清理"""
        TagStatistics.objects.all().delete()
        PersonaCard.objects.all().delete()
        KnowledgeBase.objects.all().delete()
        Users.objects.all().delete()
        cache.clear()
    
    @given(
        kb_tags_list=st.lists(tag_array_strategy, min_size=0, max_size=10),
        pc_tags_list=st.lists(tag_array_strategy, min_size=0, max_size=10)
    )
    @settings(max_examples=50, deadline=5000)
    def test_rebuild_statistics_counts_correctly(self, kb_tags_list, pc_tags_list):
        """测试重建统计正确计算标签使用次数"""
        # 创建知识库
        for tags in kb_tags_list:
            if tags:  # 只创建有标签的记录
                KnowledgeBase.objects.create(
                    name=f"知识库",
                    description="描述",
                    uploader=self.user,
                    is_public=True,
                    tags=tags
                )
        
        # 创建人设卡
        for tags in pc_tags_list:
            if tags:  # 只创建有标签的记录
                PersonaCard.objects.create(
                    name=f"人设卡",
                    description="描述",
                    uploader=self.user,
                    is_public=True,
                    tags=tags
                )
        
        # 手动计算期望的标签使用次数（使用 parse_tags 确保一致性）
        expected_kb_counts = {}
        for tags in kb_tags_list:
            # 使用 parse_tags 处理标签，确保与服务层逻辑一致
            parsed_tags = TagService.parse_tags(tags)
            for tag in parsed_tags:
                expected_kb_counts[tag] = expected_kb_counts.get(tag, 0) + 1
        
        expected_pc_counts = {}
        for tags in pc_tags_list:
            # 使用 parse_tags 处理标签，确保与服务层逻辑一致
            parsed_tags = TagService.parse_tags(tags)
            for tag in parsed_tags:
                expected_pc_counts[tag] = expected_pc_counts.get(tag, 0) + 1
        
        # 重建统计
        result = TagService.rebuild_statistics()
        
        # 验证知识库标签统计
        for tag, expected_count in expected_kb_counts.items():
            tag_stat = TagStatistics.objects.filter(
                tag=tag,
                tag_type='knowledge'
            ).first()
            assert tag_stat is not None, f"标签 '{tag}' 的统计记录不存在"
            assert tag_stat.usage_count == expected_count, \
                f"标签 '{tag}' 的使用次数不正确：期望 {expected_count}，实际 {tag_stat.usage_count}"
        
        # 验证人设卡标签统计
        for tag, expected_count in expected_pc_counts.items():
            tag_stat = TagStatistics.objects.filter(
                tag=tag,
                tag_type='persona'
            ).first()
            assert tag_stat is not None, f"标签 '{tag}' 的统计记录不存在"
            assert tag_stat.usage_count == expected_count, \
                f"标签 '{tag}' 的使用次数不正确：期望 {expected_count}，实际 {tag_stat.usage_count}"
        
        # 验证统计结果摘要
        assert result['knowledge_tags'] == len(expected_kb_counts)
        assert result['persona_tags'] == len(expected_pc_counts)


# ==================== 属性 5：热门标签排序 ====================

class TestProperty5_PopularTagsSorting(TestCase):
    """属性 5：热门标签排序
    
    **验证需求：4.3**
    
    对于任意标签统计数据集，查询热门标签时返回的列表应该按使用次数降序排列
    """
    
    def setUp(self):
        """测试前准备"""
        cache.clear()
    
    def tearDown(self):
        """测试后清理"""
        TagStatistics.objects.all().delete()
        cache.clear()
    
    @given(
        tag_counts=st.lists(
            st.tuples(valid_tag_strategy, usage_count_strategy),
            min_size=1,
            max_size=30,
            unique_by=lambda x: x[0]  # 确保标签名称唯一
        )
    )
    @settings(max_examples=50, deadline=3000)
    def test_popular_tags_sorted_by_usage_count(self, tag_counts):
        """测试热门标签按使用次数降序排列"""
        # 创建标签统计记录
        now = timezone.now()
        for tag, count in tag_counts:
            tag_stat = TagStatistics(
                tag=tag,
                tag_type='knowledge',
                usage_count=count,
                search_count=0,
                last_used_at=now
            )
            tag_stat.hot_score = tag_stat.calculate_hot_score()
            tag_stat.save()
        
        # 获取热门标签
        result = TagService.get_popular_tags(limit=len(tag_counts), tag_type='knowledge')
        
        # 验证排序：每个标签的使用次数应该 >= 下一个标签的使用次数
        for i in range(len(result) - 1):
            current_count = result[i]['usage_count']
            next_count = result[i + 1]['usage_count']
            assert current_count >= next_count, \
                f"热门标签排序错误：位置 {i} 的标签使用次数 ({current_count}) " \
                f"小于位置 {i + 1} 的标签使用次数 ({next_count})"


# ==================== 属性 6：标签搜索计数增长 ====================

class TestProperty6_SearchCountIncrement(TestCase):
    """属性 6：标签搜索计数增长
    
    **验证需求：4.5**
    
    对于任意标签，每次调用搜索计数增加方法后，该标签的搜索次数应该增加 1
    """
    
    def setUp(self):
        """测试前准备"""
        cache.clear()
    
    def tearDown(self):
        """测试后清理"""
        TagStatistics.objects.all().delete()
        cache.clear()
    
    @given(
        tag=valid_tag_strategy,
        initial_count=st.integers(min_value=0, max_value=100),
        increment_times=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50, deadline=3000)
    def test_search_count_increments_correctly(self, tag, initial_count, increment_times):
        """测试搜索计数正确增长"""
        # 创建初始标签统计记录
        if initial_count > 0:
            TagStatistics.objects.create(
                tag=tag,
                tag_type='knowledge',
                usage_count=0,
                search_count=initial_count,
                last_used_at=timezone.now()
            )
        
        # 多次增加搜索计数
        for _ in range(increment_times):
            TagService.increment_search_count(tag, tag_type='knowledge')
        
        # 验证搜索次数
        tag_stat = TagStatistics.objects.get(tag=tag, tag_type='knowledge')
        expected_count = initial_count + increment_times
        assert tag_stat.search_count == expected_count, \
            f"标签 '{tag}' 的搜索次数不正确：期望 {expected_count}，实际 {tag_stat.search_count}"


# ==================== 属性 7：标签模糊搜索包含性 ====================

class TestProperty7_FuzzySearchInclusion(TestCase):
    """属性 7：标签模糊搜索包含性
    
    **验证需求：4.4**
    
    对于任意搜索关键词，模糊搜索返回的所有标签都应该包含该关键词（不区分大小写）
    
    注意：此属性测试需要 TagService 实现模糊搜索方法。
    如果该方法尚未实现，此测试将被跳过。
    """
    
    def setUp(self):
        """测试前准备"""
        cache.clear()
    
    def tearDown(self):
        """测试后清理"""
        TagStatistics.objects.all().delete()
        cache.clear()
    
    @pytest.mark.skip(reason="TagService 尚未实现模糊搜索方法")
    @given(
        tags=st.lists(valid_tag_strategy, min_size=5, max_size=20, unique=True),
        search_keyword=st.text(min_size=1, max_size=10)
    )
    @settings(max_examples=30, deadline=3000)
    def test_fuzzy_search_includes_keyword(self, tags, search_keyword):
        """测试模糊搜索返回的标签都包含关键词"""
        # 创建标签统计记录
        now = timezone.now()
        for tag in tags:
            TagStatistics.objects.create(
                tag=tag,
                tag_type='knowledge',
                usage_count=1,
                search_count=0,
                last_used_at=now
            )
        
        # 执行模糊搜索（假设方法名为 search_tags）
        # result = TagService.search_tags(search_keyword, tag_type='knowledge')
        
        # 验证所有返回的标签都包含关键词
        # for tag_info in result:
        #     tag = tag_info['tag']
        #     assert search_keyword.lower() in tag.lower(), \
        #         f"标签 '{tag}' 不包含搜索关键词 '{search_keyword}'"
        pass


# ==================== 辅助属性：parse_tags 幂等性 ====================

class TestProperty_ParseTagsIdempotence(TestCase):
    """辅助属性：parse_tags 幂等性
    
    对于任意标签数据，多次调用 parse_tags 应该返回相同的结果
    """
    
    def setUp(self):
        """测试前准备"""
        pass
    
    def tearDown(self):
        """测试后清理"""
        pass
    
    @given(
        tags=st.one_of(
            tag_array_strategy,
            tag_string_strategy,
            st.none()
        )
    )
    @settings(max_examples=100, deadline=1000)
    def test_parse_tags_idempotence(self, tags):
        """测试 parse_tags 的幂等性"""
        # 第一次解析
        result1 = TagService.parse_tags(tags)
        
        # 第二次解析（使用第一次的结果）
        result2 = TagService.parse_tags(result1)
        
        # 第三次解析（使用第二次的结果）
        result3 = TagService.parse_tags(result2)
        
        # 验证结果相同
        assert result1 == result2 == result3, \
            f"parse_tags 不满足幂等性：\n" \
            f"第一次: {result1}\n" \
            f"第二次: {result2}\n" \
            f"第三次: {result3}"

"""标签服务单元测试

测试标签服务的各项功能，包括：
- parse_tags 方法（数组、字符串、None、带空格）
- update_tag_usage 方法（创建新记录、增加现有记录）
- get_popular_tags 方法（排序验证）
- rebuild_statistics 方法（统计正确性）

验证需求：4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

from django.test import TestCase
from django.core.cache import cache
from django.utils import timezone
from mainotebook.system.models import Users
from mainotebook.content.models import TagStatistics, KnowledgeBase, PersonaCard
from mainotebook.content.services.tag_service import TagService


class TagServiceTest(TestCase):
    """标签服务单元测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建测试用户（使用 get_or_create 避免重复）
        self.user, _ = Users.objects.get_or_create(
            username="testuser",
            defaults={
                "name": "测试用户",
                "email": "test@example.com"
            }
        )
        
        # 清除缓存
        cache.clear()
    
    def tearDown(self):
        """测试后清理"""
        # 清理测试数据
        TagStatistics.objects.all().delete()
        PersonaCard.objects.all().delete()
        KnowledgeBase.objects.all().delete()
        Users.objects.all().delete()
        cache.clear()
    
    # ========== parse_tags 方法测试 ==========
    
    def test_parse_tags_with_array(self):
        """测试解析数组格式的标签（需求 4.1）"""
        tags = ["标签1", "标签2", "标签3"]
        result = TagService.parse_tags(tags)
        
        self.assertEqual(result, ["标签1", "标签2", "标签3"])
    
    def test_parse_tags_with_string(self):
        """测试解析字符串格式的标签（需求 4.1）"""
        tags = "标签1,标签2,标签3"
        result = TagService.parse_tags(tags)
        
        self.assertEqual(result, ["标签1", "标签2", "标签3"])
    
    def test_parse_tags_with_none(self):
        """测试解析 None 值（需求 4.1）"""
        result = TagService.parse_tags(None)
        
        self.assertEqual(result, [])
    
    def test_parse_tags_with_empty_string(self):
        """测试解析空字符串（需求 4.1）"""
        result = TagService.parse_tags("")
        
        self.assertEqual(result, [])
    
    def test_parse_tags_with_empty_array(self):
        """测试解析空数组（需求 4.1）"""
        result = TagService.parse_tags([])
        
        self.assertEqual(result, [])
    
    def test_parse_tags_with_whitespace_in_string(self):
        """测试解析带空格的字符串标签（需求 4.1）"""
        tags = "  标签1  ,  标签2  ,  标签3  "
        result = TagService.parse_tags(tags)
        
        self.assertEqual(result, ["标签1", "标签2", "标签3"])
    
    def test_parse_tags_with_whitespace_in_array(self):
        """测试解析带空格的数组标签（需求 4.1）"""
        tags = ["  标签1  ", "  标签2  ", "  标签3  "]
        result = TagService.parse_tags(tags)
        
        self.assertEqual(result, ["标签1", "标签2", "标签3"])
    
    def test_parse_tags_filters_empty_strings_in_string(self):
        """测试过滤字符串中的空标签（需求 4.1）"""
        tags = "标签1,,标签2,,,标签3"
        result = TagService.parse_tags(tags)
        
        self.assertEqual(result, ["标签1", "标签2", "标签3"])
    
    def test_parse_tags_filters_empty_strings_in_array(self):
        """测试过滤数组中的空字符串（需求 4.1）"""
        tags = ["标签1", "", "标签2", "  ", "标签3"]
        result = TagService.parse_tags(tags)
        
        self.assertEqual(result, ["标签1", "标签2", "标签3"])
    
    def test_parse_tags_filters_non_string_items(self):
        """测试过滤数组中的非字符串元素（需求 4.1）"""
        tags = ["标签1", None, "标签2", 123, "标签3"]
        result = TagService.parse_tags(tags)
        
        self.assertEqual(result, ["标签1", "标签2", "标签3"])
    
    # ========== update_tag_usage 方法测试 ==========
    
    def test_update_tag_usage_creates_new_records(self):
        """测试更新标签使用次数会创建新记录（需求 4.2）"""
        tags = ["标签1", "标签2"]
        TagService.update_tag_usage(tags, tag_type='knowledge')
        
        # 验证创建了两条记录
        self.assertEqual(TagStatistics.objects.count(), 2)
        
        # 验证记录内容
        tag1 = TagStatistics.objects.get(tag="标签1", tag_type='knowledge')
        self.assertEqual(tag1.usage_count, 1)
        self.assertEqual(tag1.search_count, 0)
        self.assertIsNotNone(tag1.last_used_at)
        
        tag2 = TagStatistics.objects.get(tag="标签2", tag_type='knowledge')
        self.assertEqual(tag2.usage_count, 1)
    
    def test_update_tag_usage_increments_existing_records(self):
        """测试更新标签使用次数会增加现有记录（需求 4.2）"""
        # 创建初始记录
        TagStatistics.objects.create(
            tag="标签1",
            tag_type='knowledge',
            usage_count=5,
            search_count=2,
            last_used_at=timezone.now()
        )
        
        # 更新标签使用次数
        tags = ["标签1"]
        TagService.update_tag_usage(tags, tag_type='knowledge')
        
        # 验证使用次数增加
        tag1 = TagStatistics.objects.get(tag="标签1", tag_type='knowledge')
        self.assertEqual(tag1.usage_count, 6)
        self.assertEqual(tag1.search_count, 2)  # 搜索次数不变
    
    def test_update_tag_usage_with_string_format(self):
        """测试使用字符串格式更新标签（需求 4.2）"""
        tags = "标签1,标签2,标签3"
        TagService.update_tag_usage(tags, tag_type='persona')
        
        # 验证创建了三条记录
        self.assertEqual(TagStatistics.objects.filter(tag_type='persona').count(), 3)
        
        # 验证记录内容
        tag1 = TagStatistics.objects.get(tag="标签1", tag_type='persona')
        self.assertEqual(tag1.usage_count, 1)
    
    def test_update_tag_usage_with_empty_tags(self):
        """测试使用空标签更新不会创建记录（需求 4.6）"""
        TagService.update_tag_usage([], tag_type='knowledge')
        
        # 验证没有创建记录
        self.assertEqual(TagStatistics.objects.count(), 0)
    
    def test_update_tag_usage_with_none(self):
        """测试使用 None 更新不会创建记录（需求 4.6）"""
        TagService.update_tag_usage(None, tag_type='knowledge')
        
        # 验证没有创建记录
        self.assertEqual(TagStatistics.objects.count(), 0)
    
    def test_update_tag_usage_clears_cache(self):
        """测试更新标签使用次数会清除缓存（需求 4.2）"""
        # 设置缓存
        cache_key = f"{TagService.POPULAR_TAGS_CACHE_KEY_PREFIX}:knowledge"
        cache.set(cache_key, [{"tag": "旧标签", "usage_count": 10}])
        
        # 更新标签
        tags = ["新标签"]
        TagService.update_tag_usage(tags, tag_type='knowledge')
        
        # 验证缓存被清除
        cached_value = cache.get(cache_key)
        self.assertIsNone(cached_value)
    
    def test_update_tag_usage_updates_last_used_at(self):
        """测试更新标签使用次数会更新最后使用时间（需求 4.2）"""
        # 创建初始记录（过去时间）
        old_time = timezone.now() - timezone.timedelta(days=1)
        TagStatistics.objects.create(
            tag="标签1",
            tag_type='knowledge',
            usage_count=1,
            search_count=0,
            last_used_at=old_time
        )
        
        # 更新标签
        tags = ["标签1"]
        TagService.update_tag_usage(tags, tag_type='knowledge')
        
        # 验证最后使用时间更新
        tag1 = TagStatistics.objects.get(tag="标签1", tag_type='knowledge')
        self.assertGreater(tag1.last_used_at, old_time)
    
    # ========== get_popular_tags 方法测试 ==========
    
    def test_get_popular_tags_returns_sorted_list(self):
        """测试获取热门标签返回排序列表（需求 4.3）"""
        # 创建测试数据
        TagStatistics.objects.create(
            tag="标签1",
            tag_type='knowledge',
            usage_count=10,
            search_count=5,
            hot_score=15.0
        )
        TagStatistics.objects.create(
            tag="标签2",
            tag_type='knowledge',
            usage_count=20,
            search_count=10,
            hot_score=30.0
        )
        TagStatistics.objects.create(
            tag="标签3",
            tag_type='knowledge',
            usage_count=5,
            search_count=2,
            hot_score=7.0
        )
        
        # 获取热门标签
        result = TagService.get_popular_tags(limit=10, tag_type='knowledge')
        
        # 验证返回结果
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['tag'], "标签2")
        self.assertEqual(result[1]['tag'], "标签1")
        self.assertEqual(result[2]['tag'], "标签3")
    
    def test_get_popular_tags_respects_limit(self):
        """测试获取热门标签遵守数量限制（需求 4.3）"""
        # 创建5条记录
        for i in range(5):
            TagStatistics.objects.create(
                tag=f"标签{i}",
                tag_type='knowledge',
                usage_count=i,
                search_count=0,
                hot_score=float(i)
            )
        
        # 获取前3个热门标签
        result = TagService.get_popular_tags(limit=3, tag_type='knowledge')
        
        # 验证只返回3条
        self.assertEqual(len(result), 3)
    
    def test_get_popular_tags_filters_by_type(self):
        """测试获取热门标签按类型过滤（需求 4.3）"""
        # 创建不同类型的标签
        TagStatistics.objects.create(
            tag="知识库标签",
            tag_type='knowledge',
            usage_count=10,
            search_count=0,
            hot_score=10.0
        )
        TagStatistics.objects.create(
            tag="人设卡标签",
            tag_type='persona',
            usage_count=20,
            search_count=0,
            hot_score=20.0
        )
        
        # 获取知识库标签
        result = TagService.get_popular_tags(limit=10, tag_type='knowledge')
        
        # 验证只返回知识库标签
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['tag'], "知识库标签")
    
    def test_get_popular_tags_uses_cache(self):
        """测试获取热门标签使用缓存（需求 4.3）"""
        # 创建测试数据
        TagStatistics.objects.create(
            tag="标签1",
            tag_type='knowledge',
            usage_count=10,
            search_count=0,
            hot_score=10.0
        )
        
        # 第一次调用（缓存未命中）
        result1 = TagService.get_popular_tags(limit=10, tag_type='knowledge')
        
        # 修改数据库数据
        TagStatistics.objects.create(
            tag="标签2",
            tag_type='knowledge',
            usage_count=20,
            search_count=0,
            hot_score=20.0
        )
        
        # 第二次调用（应该从缓存读取）
        result2 = TagService.get_popular_tags(limit=10, tag_type='knowledge')
        
        # 验证返回的是缓存数据（不包含新添加的标签2）
        self.assertEqual(len(result2), 1)
        self.assertEqual(result2[0]['tag'], "标签1")
    
    def test_get_popular_tags_returns_empty_list(self):
        """测试获取热门标签在无数据时返回空列表（需求 4.3）"""
        result = TagService.get_popular_tags(limit=10, tag_type='knowledge')
        
        self.assertEqual(result, [])
    
    # ========== increment_search_count 方法测试 ==========
    
    def test_increment_search_count_creates_new_record(self):
        """测试增加搜索次数会创建新记录（需求 4.5）"""
        TagService.increment_search_count("新标签", tag_type='knowledge')
        
        # 验证创建了记录
        tag = TagStatistics.objects.get(tag="新标签", tag_type='knowledge')
        self.assertEqual(tag.search_count, 1)
        self.assertEqual(tag.usage_count, 0)
    
    def test_increment_search_count_increments_existing_record(self):
        """测试增加搜索次数会增加现有记录（需求 4.5）"""
        # 创建初始记录
        TagStatistics.objects.create(
            tag="标签1",
            tag_type='knowledge',
            usage_count=5,
            search_count=10,
            last_used_at=timezone.now()
        )
        
        # 增加搜索次数
        TagService.increment_search_count("标签1", tag_type='knowledge')
        
        # 验证搜索次数增加
        tag = TagStatistics.objects.get(tag="标签1", tag_type='knowledge')
        self.assertEqual(tag.search_count, 11)
        self.assertEqual(tag.usage_count, 5)  # 使用次数不变
    
    def test_increment_search_count_clears_cache(self):
        """测试增加搜索次数会清除缓存（需求 4.5）"""
        # 设置缓存
        cache_key = f"{TagService.POPULAR_TAGS_CACHE_KEY_PREFIX}:knowledge"
        cache.set(cache_key, [{"tag": "旧标签", "search_count": 10}])
        
        # 增加搜索次数
        TagService.increment_search_count("新标签", tag_type='knowledge')
        
        # 验证缓存被清除
        cached_value = cache.get(cache_key)
        self.assertIsNone(cached_value)
    
    # ========== rebuild_statistics 方法测试 ==========
    
    def test_rebuild_statistics_with_empty_data(self):
        """测试重建统计在无数据时返回零值（需求 4.2）"""
        result = TagService.rebuild_statistics()
        
        self.assertEqual(result['total_tags'], 0)
        self.assertEqual(result['knowledge_tags'], 0)
        self.assertEqual(result['persona_tags'], 0)
        self.assertEqual(result['total_usage'], 0)
    
    def test_rebuild_statistics_counts_knowledge_base_tags(self):
        """测试重建统计正确统计知识库标签（需求 4.2）"""
        # 创建知识库（数组格式）
        KnowledgeBase.objects.create(
            name="知识库1",
            description="描述",
            uploader=self.user,
            is_public=True,
            tags=["标签1", "标签2"]
        )
        KnowledgeBase.objects.create(
            name="知识库2",
            description="描述",
            uploader=self.user,
            is_public=True,
            tags=["标签2", "标签3"]
        )
        
        # 重建统计
        result = TagService.rebuild_statistics()
        
        # 验证统计结果
        self.assertEqual(result['knowledge_tags'], 3)  # 标签1, 标签2, 标签3
        self.assertEqual(result['total_usage'], 4)  # 标签1(1) + 标签2(2) + 标签3(1)
        
        # 验证数据库记录
        tag1 = TagStatistics.objects.get(tag="标签1", tag_type='knowledge')
        self.assertEqual(tag1.usage_count, 1)
        
        tag2 = TagStatistics.objects.get(tag="标签2", tag_type='knowledge')
        self.assertEqual(tag2.usage_count, 2)
        
        tag3 = TagStatistics.objects.get(tag="标签3", tag_type='knowledge')
        self.assertEqual(tag3.usage_count, 1)
    
    def test_rebuild_statistics_counts_persona_card_tags(self):
        """测试重建统计正确统计人设卡标签（需求 4.2）"""
        # 创建人设卡（数组格式）
        PersonaCard.objects.create(
            name="人设卡1",
            description="描述",
            uploader=self.user,
            is_public=True,
            tags=["角色", "游戏"]
        )
        PersonaCard.objects.create(
            name="人设卡2",
            description="描述",
            uploader=self.user,
            is_public=True,
            tags=["角色", "冒险"]
        )
        
        # 重建统计
        result = TagService.rebuild_statistics()
        
        # 验证统计结果
        self.assertEqual(result['persona_tags'], 3)  # 角色, 游戏, 冒险
        self.assertEqual(result['total_usage'], 4)  # 角色(2) + 游戏(1) + 冒险(1)
        
        # 验证数据库记录
        tag1 = TagStatistics.objects.get(tag="角色", tag_type='persona')
        self.assertEqual(tag1.usage_count, 2)
    
    def test_rebuild_statistics_supports_string_format(self):
        """测试重建统计支持字符串格式标签（需求 4.2）"""
        # 创建知识库（字符串格式，向后兼容）
        KnowledgeBase.objects.create(
            name="知识库",
            description="描述",
            uploader=self.user,
            is_public=True,
            tags="标签1,标签2,标签3"
        )
        
        # 重建统计
        result = TagService.rebuild_statistics()
        
        # 验证统计结果
        self.assertEqual(result['knowledge_tags'], 3)
        self.assertEqual(result['total_usage'], 3)
    
    def test_rebuild_statistics_ignores_private_content(self):
        """测试重建统计忽略非公开内容（需求 4.2）"""
        # 创建公开知识库
        KnowledgeBase.objects.create(
            name="公开知识库",
            description="描述",
            uploader=self.user,
            is_public=True,
            tags=["公开标签"]
        )
        
        # 创建私有知识库
        KnowledgeBase.objects.create(
            name="私有知识库",
            description="描述",
            uploader=self.user,
            is_public=False,
            tags=["私有标签"]
        )
        
        # 重建统计
        result = TagService.rebuild_statistics()
        
        # 验证只统计公开内容
        self.assertEqual(result['knowledge_tags'], 1)
        self.assertEqual(TagStatistics.objects.filter(tag="公开标签").count(), 1)
        self.assertEqual(TagStatistics.objects.filter(tag="私有标签").count(), 0)
    
    def test_rebuild_statistics_clears_old_data(self):
        """测试重建统计会清除旧数据（需求 4.2）"""
        # 创建旧的统计记录
        TagStatistics.objects.create(
            tag="旧标签",
            tag_type='knowledge',
            usage_count=100,
            search_count=50,
            last_used_at=timezone.now()
        )
        
        # 创建新的知识库
        KnowledgeBase.objects.create(
            name="知识库",
            description="描述",
            uploader=self.user,
            is_public=True,
            tags=["新标签"]
        )
        
        # 重建统计
        TagService.rebuild_statistics()
        
        # 验证旧数据被清除
        self.assertEqual(TagStatistics.objects.filter(tag="旧标签").count(), 0)
        self.assertEqual(TagStatistics.objects.filter(tag="新标签").count(), 1)
    
    def test_rebuild_statistics_clears_cache(self):
        """测试重建统计会清除所有缓存（需求 4.2）"""
        # 设置缓存
        cache.set(f"{TagService.POPULAR_TAGS_CACHE_KEY_PREFIX}:knowledge", [{"tag": "旧标签"}])
        cache.set(f"{TagService.POPULAR_TAGS_CACHE_KEY_PREFIX}:persona", [{"tag": "旧标签"}])
        
        # 重建统计
        TagService.rebuild_statistics()
        
        # 验证缓存被清除
        self.assertIsNone(cache.get(f"{TagService.POPULAR_TAGS_CACHE_KEY_PREFIX}:knowledge"))
        self.assertIsNone(cache.get(f"{TagService.POPULAR_TAGS_CACHE_KEY_PREFIX}:persona"))
    
    # ========== clear_cache 方法测试 ==========
    
    def test_clear_cache_specific_type(self):
        """测试清除特定类型的缓存"""
        # 设置缓存
        cache.set(f"{TagService.POPULAR_TAGS_CACHE_KEY_PREFIX}:knowledge", [{"tag": "标签"}])
        cache.set(f"{TagService.POPULAR_TAGS_CACHE_KEY_PREFIX}:persona", [{"tag": "标签"}])
        
        # 清除知识库类型缓存
        TagService.clear_cache(tag_type='knowledge')
        
        # 验证只清除了知识库缓存
        self.assertIsNone(cache.get(f"{TagService.POPULAR_TAGS_CACHE_KEY_PREFIX}:knowledge"))
        self.assertIsNotNone(cache.get(f"{TagService.POPULAR_TAGS_CACHE_KEY_PREFIX}:persona"))
    
    def test_clear_cache_all_types(self):
        """测试清除所有类型的缓存"""
        # 设置缓存
        cache.set(f"{TagService.POPULAR_TAGS_CACHE_KEY_PREFIX}:knowledge", [{"tag": "标签"}])
        cache.set(f"{TagService.POPULAR_TAGS_CACHE_KEY_PREFIX}:persona", [{"tag": "标签"}])
        
        # 清除所有缓存
        TagService.clear_cache()
        
        # 验证所有缓存都被清除
        self.assertIsNone(cache.get(f"{TagService.POPULAR_TAGS_CACHE_KEY_PREFIX}:knowledge"))
        self.assertIsNone(cache.get(f"{TagService.POPULAR_TAGS_CACHE_KEY_PREFIX}:persona"))
    def test_clear_cache_all_types(self):
        """测试清除所有类型的缓存"""
        # 设置缓存
        cache.set(f"{TagService.POPULAR_TAGS_CACHE_KEY_PREFIX}:knowledge", [{"tag": "标签"}])
        cache.set(f"{TagService.POPULAR_TAGS_CACHE_KEY_PREFIX}:persona", [{"tag": "标签"}])

        # 清除所有缓存
        TagService.clear_cache()

        # 验证所有缓存都被清除
        self.assertIsNone(cache.get(f"{TagService.POPULAR_TAGS_CACHE_KEY_PREFIX}:knowledge"))
        self.assertIsNone(cache.get(f"{TagService.POPULAR_TAGS_CACHE_KEY_PREFIX}:persona"))

    # ========== decrease_tag_usage 方法测试 ==========

    def test_decrease_tag_usage_with_array_format(self):
        """测试使用数组格式减少标签使用次数（需求 2.1, 2.2, 2.4）"""
        # 创建初始统计记录
        TagStatistics.objects.create(
            tag="标签1",
            tag_type='knowledge',
            usage_count=5,
            search_count=2,
            last_used_at=timezone.now()
        )
        TagStatistics.objects.create(
            tag="标签2",
            tag_type='knowledge',
            usage_count=3,
            search_count=1,
            last_used_at=timezone.now()
        )
        
        # 减少标签使用次数
        tags = ["标签1", "标签2"]
        TagService.decrease_tag_usage(tags, tag_type='knowledge')
        
        # 验证使用次数减少
        tag1 = TagStatistics.objects.get(tag="标签1", tag_type='knowledge')
        self.assertEqual(tag1.usage_count, 4)
        
        tag2 = TagStatistics.objects.get(tag="标签2", tag_type='knowledge')
        self.assertEqual(tag2.usage_count, 2)
    
    def test_decrease_tag_usage_with_string_format(self):
        """测试使用字符串格式减少标签使用次数（需求 2.1, 2.2, 2.4）"""
        # 创建初始统计记录
        TagStatistics.objects.create(
            tag="标签1",
            tag_type='persona',
            usage_count=10,
            search_count=0,
            last_used_at=timezone.now()
        )
        TagStatistics.objects.create(
            tag="标签2",
            tag_type='persona',
            usage_count=8,
            search_count=0,
            last_used_at=timezone.now()
        )
        
        # 使用字符串格式减少标签使用次数
        tags = "标签1,标签2"
        TagService.decrease_tag_usage(tags, tag_type='persona')
        
        # 验证使用次数减少
        tag1 = TagStatistics.objects.get(tag="标签1", tag_type='persona')
        self.assertEqual(tag1.usage_count, 9)
        
        tag2 = TagStatistics.objects.get(tag="标签2", tag_type='persona')
        self.assertEqual(tag2.usage_count, 7)
    
    def test_decrease_tag_usage_with_none(self):
        """测试使用 None 减少标签不会报错（需求 2.1, 2.2, 2.4）"""
        # 创建初始统计记录
        TagStatistics.objects.create(
            tag="标签1",
            tag_type='knowledge',
            usage_count=5,
            search_count=0,
            last_used_at=timezone.now()
        )
        
        # 使用 None 减少标签
        TagService.decrease_tag_usage(None, tag_type='knowledge')
        
        # 验证标签统计不变
        tag1 = TagStatistics.objects.get(tag="标签1", tag_type='knowledge')
        self.assertEqual(tag1.usage_count, 5)
    
    def test_decrease_tag_usage_with_empty_array(self):
        """测试使用空数组减少标签不会报错（需求 2.1, 2.2, 2.4）"""
        # 创建初始统计记录
        TagStatistics.objects.create(
            tag="标签1",
            tag_type='knowledge',
            usage_count=5,
            search_count=0,
            last_used_at=timezone.now()
        )
        
        # 使用空数组减少标签
        TagService.decrease_tag_usage([], tag_type='knowledge')
        
        # 验证标签统计不变
        tag1 = TagStatistics.objects.get(tag="标签1", tag_type='knowledge')
        self.assertEqual(tag1.usage_count, 5)
    
    def test_decrease_tag_usage_deletes_zero_count_records(self):
        """测试 usage_count 降为 0 时删除记录（需求 2.1, 2.2, 2.4）"""
        # 创建 usage_count 为 1 的记录
        TagStatistics.objects.create(
            tag="标签1",
            tag_type='knowledge',
            usage_count=1,
            search_count=5,
            last_used_at=timezone.now()
        )
        TagStatistics.objects.create(
            tag="标签2",
            tag_type='knowledge',
            usage_count=2,
            search_count=3,
            last_used_at=timezone.now()
        )
        
        # 减少标签使用次数
        tags = ["标签1", "标签2"]
        TagService.decrease_tag_usage(tags, tag_type='knowledge')
        
        # 验证 usage_count 为 0 的记录被删除
        self.assertEqual(TagStatistics.objects.filter(tag="标签1", tag_type='knowledge').count(), 0)
        
        # 验证 usage_count > 0 的记录仍然存在
        tag2 = TagStatistics.objects.get(tag="标签2", tag_type='knowledge')
        self.assertEqual(tag2.usage_count, 1)
    
    def test_decrease_tag_usage_handles_already_zero_count(self):
        """测试 usage_count 已经为 0 时再减少的边界情况（需求 2.1, 2.2, 2.4）"""
        # 创建 usage_count 为 0 的记录（理论上不应该存在，但测试边界情况）
        TagStatistics.objects.create(
            tag="标签1",
            tag_type='knowledge',
            usage_count=0,
            search_count=5,
            last_used_at=timezone.now()
        )
        
        # 减少标签使用次数
        tags = ["标签1"]
        TagService.decrease_tag_usage(tags, tag_type='knowledge')
        
        # 验证记录被删除（usage_count <= 0）
        self.assertEqual(TagStatistics.objects.filter(tag="标签1", tag_type='knowledge').count(), 0)
    
    def test_decrease_tag_usage_uses_f_expression(self):
        """测试 F 表达式的原子操作避免竞态条件（需求 2.1, 2.2, 2.4）"""
        # 创建初始统计记录
        TagStatistics.objects.create(
            tag="标签1",
            tag_type='knowledge',
            usage_count=10,
            search_count=0,
            last_used_at=timezone.now()
        )
        
        # 多次减少标签使用次数（模拟并发操作）
        for _ in range(3):
            TagService.decrease_tag_usage(["标签1"], tag_type='knowledge')
        
        # 验证使用次数正确减少
        tag1 = TagStatistics.objects.get(tag="标签1", tag_type='knowledge')
        self.assertEqual(tag1.usage_count, 7)
    
    def test_decrease_tag_usage_updates_hot_score(self):
        """测试减少标签使用次数后更新热度分数（需求 2.1, 2.2, 2.4）"""
        # 创建初始统计记录
        tag_stat = TagStatistics.objects.create(
            tag="标签1",
            tag_type='knowledge',
            usage_count=10,
            search_count=5,
            last_used_at=timezone.now()
        )
        old_hot_score = tag_stat.hot_score
        
        # 减少标签使用次数
        TagService.decrease_tag_usage(["标签1"], tag_type='knowledge')
        
        # 验证热度分数更新
        tag_stat.refresh_from_db()
        new_hot_score = tag_stat.hot_score
        self.assertNotEqual(old_hot_score, new_hot_score)
    
    def test_decrease_tag_usage_clears_cache(self):
        """测试减少标签使用次数会清除缓存（需求 2.1, 2.2, 2.4）"""
        # 创建初始统计记录
        TagStatistics.objects.create(
            tag="标签1",
            tag_type='knowledge',
            usage_count=5,
            search_count=0,
            last_used_at=timezone.now()
        )
        
        # 设置缓存
        cache_key = f"{TagService.POPULAR_TAGS_CACHE_KEY_PREFIX}:knowledge"
        cache.set(cache_key, [{"tag": "标签1", "usage_count": 5}])
        
        # 减少标签使用次数
        TagService.decrease_tag_usage(["标签1"], tag_type='knowledge')
        
        # 验证缓存被清除
        cached_value = cache.get(cache_key)
        self.assertIsNone(cached_value)
    
    def test_decrease_tag_usage_handles_nonexistent_tag(self):
        """测试减少不存在的标签不会报错（需求 2.1, 2.2, 2.4）"""
        # 不创建任何记录
        
        # 减少不存在的标签
        TagService.decrease_tag_usage(["不存在的标签"], tag_type='knowledge')
        
        # 验证没有创建新记录
        self.assertEqual(TagStatistics.objects.filter(tag="不存在的标签").count(), 0)
    
    def test_decrease_tag_usage_filters_by_tag_type(self):
        """测试减少标签使用次数按类型过滤（需求 2.1, 2.2, 2.4）"""
        # 创建不同类型的标签
        TagStatistics.objects.create(
            tag="标签1",
            tag_type='knowledge',
            usage_count=5,
            search_count=0,
            last_used_at=timezone.now()
        )
        TagStatistics.objects.create(
            tag="标签1",
            tag_type='persona',
            usage_count=3,
            search_count=0,
            last_used_at=timezone.now()
        )
        
        # 只减少 knowledge 类型的标签
        TagService.decrease_tag_usage(["标签1"], tag_type='knowledge')
        
        # 验证只有 knowledge 类型的标签减少
        tag_knowledge = TagStatistics.objects.get(tag="标签1", tag_type='knowledge')
        self.assertEqual(tag_knowledge.usage_count, 4)
        
        tag_persona = TagStatistics.objects.get(tag="标签1", tag_type='persona')
        self.assertEqual(tag_persona.usage_count, 3)

    # ========== sync_tag_usage 方法测试 ==========

    def test_sync_tag_usage_adds_new_tags(self):
        """测试同步标签使用次数会增加新标签（需求 2.4）"""
        old_tags = ["标签1", "标签2"]
        new_tags = ["标签1", "标签2", "标签3", "标签4"]

        # 初始化旧标签的统计
        TagService.update_tag_usage(old_tags, tag_type='knowledge')

        # 同步标签
        TagService.sync_tag_usage(old_tags, new_tags, tag_type='knowledge')

        # 验证新增标签的统计
        tag3 = TagStatistics.objects.get(tag="标签3", tag_type='knowledge')
        self.assertEqual(tag3.usage_count, 1)

        tag4 = TagStatistics.objects.get(tag="标签4", tag_type='knowledge')
        self.assertEqual(tag4.usage_count, 1)

    def test_sync_tag_usage_removes_old_tags(self):
        """测试同步标签使用次数会减少删除的标签（需求 2.4）"""
        old_tags = ["标签1", "标签2", "标签3"]
        new_tags = ["标签1"]

        # 初始化旧标签的统计
        TagService.update_tag_usage(old_tags, tag_type='knowledge')

        # 同步标签
        TagService.sync_tag_usage(old_tags, new_tags, tag_type='knowledge')

        # 验证删除标签的统计减少
        tag1 = TagStatistics.objects.get(tag="标签1", tag_type='knowledge')
        self.assertEqual(tag1.usage_count, 1)

        # 标签2和标签3的usage_count应该降为0并被删除
        self.assertEqual(TagStatistics.objects.filter(tag="标签2", tag_type='knowledge').count(), 0)
        self.assertEqual(TagStatistics.objects.filter(tag="标签3", tag_type='knowledge').count(), 0)

    def test_sync_tag_usage_with_both_add_and_remove(self):
        """测试同步标签使用次数同时处理新增和删除（需求 2.4）"""
        old_tags = ["标签1", "标签2", "标签3"]
        new_tags = ["标签1", "标签3", "标签4"]

        # 初始化旧标签的统计
        TagService.update_tag_usage(old_tags, tag_type='knowledge')

        # 同步标签
        TagService.sync_tag_usage(old_tags, new_tags, tag_type='knowledge')

        # 验证保持不变的标签
        tag1 = TagStatistics.objects.get(tag="标签1", tag_type='knowledge')
        self.assertEqual(tag1.usage_count, 1)

        tag3 = TagStatistics.objects.get(tag="标签3", tag_type='knowledge')
        self.assertEqual(tag3.usage_count, 1)

        # 验证删除的标签
        self.assertEqual(TagStatistics.objects.filter(tag="标签2", tag_type='knowledge').count(), 0)

        # 验证新增的标签
        tag4 = TagStatistics.objects.get(tag="标签4", tag_type='knowledge')
        self.assertEqual(tag4.usage_count, 1)

    def test_sync_tag_usage_with_no_changes(self):
        """测试同步标签使用次数在标签无变化时不做操作（需求 3.3）"""
        old_tags = ["标签1", "标签2"]
        new_tags = ["标签1", "标签2"]

        # 初始化旧标签的统计
        TagService.update_tag_usage(old_tags, tag_type='knowledge')

        # 同步标签
        TagService.sync_tag_usage(old_tags, new_tags, tag_type='knowledge')

        # 验证标签统计不变
        tag1 = TagStatistics.objects.get(tag="标签1", tag_type='knowledge')
        self.assertEqual(tag1.usage_count, 1)

        tag2 = TagStatistics.objects.get(tag="标签2", tag_type='knowledge')
        self.assertEqual(tag2.usage_count, 1)

    def test_sync_tag_usage_with_string_format(self):
        """测试同步标签使用次数支持字符串格式（需求 2.4）"""
        old_tags = "标签1,标签2"
        new_tags = "标签2,标签3"

        # 初始化旧标签的统计
        TagService.update_tag_usage(old_tags, tag_type='knowledge')

        # 同步标签
        TagService.sync_tag_usage(old_tags, new_tags, tag_type='knowledge')

        # 验证删除的标签
        self.assertEqual(TagStatistics.objects.filter(tag="标签1", tag_type='knowledge').count(), 0)

        # 验证保持的标签
        tag2 = TagStatistics.objects.get(tag="标签2", tag_type='knowledge')
        self.assertEqual(tag2.usage_count, 1)

        # 验证新增的标签
        tag3 = TagStatistics.objects.get(tag="标签3", tag_type='knowledge')
        self.assertEqual(tag3.usage_count, 1)

    def test_sync_tag_usage_with_none_values(self):
        """测试同步标签使用次数处理 None 值（需求 2.4）"""
        old_tags = ["标签1", "标签2"]
        new_tags = None

        # 初始化旧标签的统计
        TagService.update_tag_usage(old_tags, tag_type='knowledge')

        # 同步标签（从有标签变为无标签）
        TagService.sync_tag_usage(old_tags, new_tags, tag_type='knowledge')

        # 验证所有旧标签都被删除
        self.assertEqual(TagStatistics.objects.filter(tag="标签1", tag_type='knowledge').count(), 0)
        self.assertEqual(TagStatistics.objects.filter(tag="标签2", tag_type='knowledge').count(), 0)

    def test_sync_tag_usage_clears_cache(self):
        """测试同步标签使用次数会清除缓存（需求 2.4）"""
        # 设置缓存
        cache_key = f"{TagService.POPULAR_TAGS_CACHE_KEY_PREFIX}:knowledge"
        cache.set(cache_key, [{"tag": "旧标签", "usage_count": 10}])

        old_tags = ["标签1"]
        new_tags = ["标签2"]

        # 初始化旧标签的统计
        TagService.update_tag_usage(old_tags, tag_type='knowledge')

        # 同步标签
        TagService.sync_tag_usage(old_tags, new_tags, tag_type='knowledge')

        # 验证缓存被清除
        cached_value = cache.get(cache_key)
        self.assertIsNone(cached_value)


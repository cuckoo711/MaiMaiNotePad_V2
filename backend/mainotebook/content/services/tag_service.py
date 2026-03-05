"""
标签统计服务

提供标签统计、热门标签查询、缓存管理等功能。
"""

from typing import List, Dict, Union
from django.core.cache import cache
from django.db.models import F
from django.utils import timezone
from mainotebook.content.models import TagStatistics, KnowledgeBase, PersonaCard


class TagService:
    """标签服务类"""
    
    # 缓存键前缀
    POPULAR_TAGS_CACHE_KEY_PREFIX = "content:popular_tags"
    # 缓存过期时间（秒）
    CACHE_TIMEOUT = 3600  # 1小时
    
    @classmethod
    def parse_tags(cls, tags: Union[List[str], str, None]) -> List[str]:
        """解析标签数据
        
        统一处理标签的解析逻辑，支持数组和字符串格式。
        
        Args:
            tags: 标签数据，可以是数组、字符串或 None
            
        Returns:
            List[str]: 标签数组
        """
        if tags is None:
            return []
        
        if isinstance(tags, str):
            return [tag.strip() for tag in tags.split(',') if tag.strip()]
        
        if isinstance(tags, list):
            return [tag.strip() for tag in tags if tag and isinstance(tag, str) and tag.strip()]
        
        return []
    
    @classmethod
    def get_popular_tags(cls, limit: int = 20, tag_type: str = 'knowledge') -> List[Dict[str, any]]:
        """获取热门标签列表
        
        优先从缓存读取，缓存未命中时从数据库查询并更新缓存。
        
        Args:
            limit: 返回的标签数量，默认20个
            tag_type: 标签类型，'knowledge' 或 'persona'，默认 'knowledge'
            
        Returns:
            List[Dict]: 热门标签列表，每个元素包含 tag, usage_count, search_count, hot_score
        """
        # 构建缓存键
        cache_key = f"{cls.POPULAR_TAGS_CACHE_KEY_PREFIX}:{tag_type}"
        
        # 尝试从缓存获取
        cached_tags = cache.get(cache_key)
        if cached_tags is not None:
            return cached_tags[:limit]
        
        # 缓存未命中，从数据库查询
        tags = TagStatistics.objects.filter(tag_type=tag_type).all()[:limit]
        result = [
            {
                'tag': tag.tag,
                'usage_count': tag.usage_count,
                'search_count': tag.search_count,
                'hot_score': tag.hot_score,
            }
            for tag in tags
        ]
        
        # 更新缓存
        cache.set(cache_key, result, cls.CACHE_TIMEOUT)
        
        return result
    
    @classmethod
    def increment_search_count(cls, tag: str, tag_type: str = 'knowledge') -> None:
        """增加标签搜索次数
        
        当用户通过标签筛选时调用此方法。
        
        Args:
            tag: 标签名称
            tag_type: 标签类型，'knowledge' 或 'persona'，默认 'knowledge'
        """
        tag_stat, created = TagStatistics.objects.get_or_create(
            tag=tag,
            tag_type=tag_type,
            defaults={'search_count': 1, 'usage_count': 0}
        )
        
        if not created:
            # 使用 F 表达式避免竞态条件
            TagStatistics.objects.filter(tag=tag, tag_type=tag_type).update(
                search_count=F('search_count') + 1
            )
            # 重新获取对象以更新热度分数
            tag_stat.refresh_from_db()
        
        tag_stat.update_hot_score()
        
        # 清除对应类型的缓存
        cache_key = f"{cls.POPULAR_TAGS_CACHE_KEY_PREFIX}:{tag_type}"
        cache.delete(cache_key)
    
    @classmethod
    def update_tag_usage(cls, tags: Union[List[str], str], tag_type: str = 'knowledge') -> None:
        """更新标签使用次数
        
        当创建或更新知识库/人设卡时调用此方法。
        
        Args:
            tags: 标签数据（数组或字符串）
            tag_type: 标签类型，'knowledge' 或 'persona'，默认 'knowledge'
        """
        tag_list = cls.parse_tags(tags)
        
        if not tag_list:
            return
        
        now = timezone.now()
        
        for tag in tag_list:
            tag = tag.strip()
            if not tag:
                continue
            
            tag_stat, created = TagStatistics.objects.get_or_create(
                tag=tag,
                tag_type=tag_type,
                defaults={
                    'usage_count': 1,
                    'search_count': 0,
                    'last_used_at': now
                }
            )
            
            if not created:
                TagStatistics.objects.filter(tag=tag, tag_type=tag_type).update(
                    usage_count=F('usage_count') + 1,
                    last_used_at=now
                )
                tag_stat.refresh_from_db()
            
            tag_stat.update_hot_score()
        
        # 清除对应类型的缓存
        cache_key = f"{cls.POPULAR_TAGS_CACHE_KEY_PREFIX}:{tag_type}"
        cache.delete(cache_key)
    
    @classmethod
    def decrease_tag_usage(cls, tags: Union[List[str], str], tag_type: str = 'knowledge') -> None:
        """减少标签使用次数
        
        当删除或将公开内容设为私有时调用此方法。
        使用 F 表达式原子减少 usage_count，避免竞态条件。
        当 usage_count 降为 0 时，自动删除 TagStatistics 记录。
        
        Args:
            tags: 标签数据（数组或字符串）
            tag_type: 标签类型，'knowledge' 或 'persona'，默认 'knowledge'
        """
        tag_list = cls.parse_tags(tags)
        
        if not tag_list:
            return
        
        for tag in tag_list:
            tag = tag.strip()
            if not tag:
                continue
            
            # 使用 F 表达式原子减少 usage_count
            TagStatistics.objects.filter(tag=tag, tag_type=tag_type).update(
                usage_count=F('usage_count') - 1
            )
        
        # 查询并删除 usage_count <= 0 的记录
        TagStatistics.objects.filter(
            tag__in=tag_list,
            tag_type=tag_type,
            usage_count__lte=0
        ).delete()
        
        # 对剩余记录更新 hot_score
        remaining_tags = TagStatistics.objects.filter(
            tag__in=tag_list,
            tag_type=tag_type
        )
        for tag_stat in remaining_tags:
            tag_stat.update_hot_score()
        
        # 清除对应类型的缓存
        cache_key = f"{cls.POPULAR_TAGS_CACHE_KEY_PREFIX}:{tag_type}"
        cache.delete(cache_key)
    @classmethod
    def sync_tag_usage(cls, old_tags: Union[List[str], str, None], new_tags: Union[List[str], str, None], tag_type: str = 'knowledge') -> None:
        """同步标签使用次数

        当更新内容的标签列表时调用此方法。
        计算标签差异，对新增标签增加 usage_count，对删除标签减少 usage_count。

        Args:
            old_tags: 旧标签数据（数组或字符串）
            new_tags: 新标签数据（数组或字符串）
            tag_type: 标签类型，'knowledge' 或 'persona'，默认 'knowledge'
        """
        # 解析新旧标签
        old_tag_list = set(cls.parse_tags(old_tags))
        new_tag_list = set(cls.parse_tags(new_tags))

        # 计算标签差异
        added_tags = new_tag_list - old_tag_list
        removed_tags = old_tag_list - new_tag_list

        # 对新增标签调用 update_tag_usage()
        if added_tags:
            cls.update_tag_usage(list(added_tags), tag_type)

        # 对删除标签调用 decrease_tag_usage()
        if removed_tags:
            cls.decrease_tag_usage(list(removed_tags), tag_type)

        # 清除对应类型的缓存
        cache_key = f"{cls.POPULAR_TAGS_CACHE_KEY_PREFIX}:{tag_type}"
        cache.delete(cache_key)

    
    @classmethod
    def rebuild_statistics(cls) -> Dict[str, int]:
        """重建标签统计数据
        
        扫描所有知识库和人设卡，重新统计标签使用次数。
        支持新的数组格式。
        用于定时任务或手动触发。
        
        Returns:
            Dict: 统计结果，包含处理的标签数量
        """
        # 清空现有统计
        TagStatistics.objects.all().delete()
        
        knowledge_tag_usage = {}
        persona_tag_usage = {}
        
        # 统计知识库标签（只统计公开且未删除的内容）
        for kb in KnowledgeBase.objects.filter(is_public=True):
            tags = cls.parse_tags(kb.tags)
            for tag in tags:
                knowledge_tag_usage[tag] = knowledge_tag_usage.get(tag, 0) + 1
        
        # 统计人设卡标签（只统计公开且未删除的内容）
        for pc in PersonaCard.objects.filter(is_public=True, is_deleted=False):
            tags = cls.parse_tags(pc.tags)
            for tag in tags:
                persona_tag_usage[tag] = persona_tag_usage.get(tag, 0) + 1
        
        # 批量创建统计记录
        tag_stats = []
        now = timezone.now()
        
        # 创建知识库标签统计
        for tag, count in knowledge_tag_usage.items():
            tag_stat = TagStatistics(
                tag=tag,
                tag_type='knowledge',
                usage_count=count,
                search_count=0,
                last_used_at=now
            )
            tag_stat.hot_score = tag_stat.calculate_hot_score()
            tag_stats.append(tag_stat)
        
        # 创建人设卡标签统计
        for tag, count in persona_tag_usage.items():
            tag_stat = TagStatistics(
                tag=tag,
                tag_type='persona',
                usage_count=count,
                search_count=0,
                last_used_at=now
            )
            tag_stat.hot_score = tag_stat.calculate_hot_score()
            tag_stats.append(tag_stat)
        
        TagStatistics.objects.bulk_create(tag_stats)
        
        # 清除所有缓存
        cls.clear_cache()
        
        return {
            'total_tags': len(tag_stats),
            'knowledge_tags': len(knowledge_tag_usage),
            'persona_tags': len(persona_tag_usage),
            'total_usage': sum(knowledge_tag_usage.values()) + sum(persona_tag_usage.values())
        }
    
    @classmethod
    def clear_cache(cls, tag_type: str = None) -> None:
        """清除热门标签缓存
        
        Args:
            tag_type: 标签类型，如果为 None 则清除所有类型的缓存
        """
        if tag_type:
            cache_key = f"{cls.POPULAR_TAGS_CACHE_KEY_PREFIX}:{tag_type}"
            cache.delete(cache_key)
        else:
            # 清除所有类型的缓存
            cache.delete(f"{cls.POPULAR_TAGS_CACHE_KEY_PREFIX}:knowledge")
            cache.delete(f"{cls.POPULAR_TAGS_CACHE_KEY_PREFIX}:persona")

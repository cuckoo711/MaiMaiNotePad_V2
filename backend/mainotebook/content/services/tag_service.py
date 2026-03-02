"""
标签统计服务

提供标签统计、热门标签查询、缓存管理等功能。
"""

from typing import List, Dict
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
    def update_tag_usage(cls, tags: List[str], tag_type: str = 'knowledge') -> None:
        """更新标签使用次数
        
        当创建或更新知识库/人设卡时调用此方法。
        
        Args:
            tags: 标签列表
            tag_type: 标签类型，'knowledge' 或 'persona'，默认 'knowledge'
        """
        if not tags:
            return
        
        now = timezone.now()
        
        for tag in tags:
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
    def rebuild_statistics(cls) -> Dict[str, int]:
        """重建标签统计数据
        
        扫描所有知识库和人设卡，重新统计标签使用次数。
        用于定时任务或手动触发。
        
        Returns:
            Dict: 统计结果，包含处理的标签数量
        """
        # 清空现有统计
        TagStatistics.objects.all().delete()
        
        knowledge_tag_usage = {}
        persona_tag_usage = {}
        
        # 统计知识库标签
        for kb in KnowledgeBase.objects.filter(is_public=True):
            if kb.tags:
                tags = [t.strip() for t in kb.tags.split(',') if t.strip()]
                for tag in tags:
                    knowledge_tag_usage[tag] = knowledge_tag_usage.get(tag, 0) + 1
        
        # 统计人设卡标签
        for pc in PersonaCard.objects.filter(is_public=True):
            if pc.tags:
                tags = [t.strip() for t in pc.tags.split(',') if t.strip()]
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
        cache.delete(f"{cls.POPULAR_TAGS_CACHE_KEY_PREFIX}:knowledge")
        cache.delete(f"{cls.POPULAR_TAGS_CACHE_KEY_PREFIX}:persona")
        
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

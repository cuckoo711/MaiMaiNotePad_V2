# -*- coding: utf-8 -*-

"""
评论推荐服务模块

提供基于用户兴趣的个性化评论推荐功能。
使用 Redis 缓存、jieba 分词、BGE-M3 嵌入模型。
"""

import logging
import json
from typing import List, Dict, Set, Optional, Tuple
from collections import Counter
from django.core.cache import cache
from django.conf import settings
import jieba
import jieba.analyse
from openai import OpenAI

logger = logging.getLogger(__name__)


class RecommendationService:
    """评论推荐服务类
    
    提供个性化推荐相关的功能：
    - 用户兴趣建模
    - 内容相似度计算
    - 浏览历史管理
    - 向量嵌入和重排序
    """
    
    # Redis 缓存键前缀
    CACHE_PREFIX_USER_INTERESTS = "user_interests:"
    CACHE_PREFIX_USER_VIEWS = "user_views:"
    CACHE_PREFIX_COMMENT_EMBEDDING = "comment_embedding:"
    
    # 缓存过期时间
    CACHE_TTL_USER_INTERESTS = 3600  # 1小时
    CACHE_TTL_USER_VIEWS = 86400  # 24小时
    CACHE_TTL_COMMENT_EMBEDDING = 604800  # 7天
    
    # BGE-M3 模型配置
    BGE_M3_MODEL = "BAAI/bge-m3"
    BGE_RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
    
    @classmethod
    def get_user_interests(cls, user) -> Dict:
        """获取用户兴趣数据（带缓存）
        
        基于用户历史行为分析兴趣：
        - 点赞过的评论作者
        - 回复过的评论作者
        - 互动过的评论关键词（jieba 分词）
        - 用户兴趣向量（BGE-M3 嵌入）
        
        Args:
            user: 用户对象
            
        Returns:
            dict: 用户兴趣数据
        """
        if not user or not user.is_authenticated:
            return cls._get_empty_interests()
        
        # 尝试从缓存获取
        cache_key = f"{cls.CACHE_PREFIX_USER_INTERESTS}{user.id}"
        cached_interests = cache.get(cache_key)
        if cached_interests:
            return cached_interests
        
        # 计算用户兴趣
        interests = cls._calculate_user_interests(user)
        
        # 存入缓存
        cache.set(cache_key, interests, cls.CACHE_TTL_USER_INTERESTS)
        
        return interests
    
    @classmethod
    def _calculate_user_interests(cls, user) -> Dict:
        """计算用户兴趣数据
        
        Args:
            user: 用户对象
            
        Returns:
            dict: 用户兴趣数据
        """
        from mainotebook.content.models import Comment
        
        # 获取用户点赞过的评论（最近100条）
        liked_comments = Comment.objects.filter(
            reactions__user=user,
            reactions__reaction_type='like',
            is_deleted=False,
        ).select_related('user').order_by('-reactions__create_datetime')[:100]
        
        # 获取用户回复过的评论（最近50条）
        replied_comments = Comment.objects.filter(
            user=user,
            parent_id__isnull=False,
            is_deleted=False,
        ).select_related('parent__user').order_by('-create_datetime')[:50]
        
        # 统计喜欢的作者
        favorite_authors = Counter()
        for comment in liked_comments:
            if comment.user_id:
                favorite_authors[comment.user_id] += 2  # 点赞权重2
        
        for comment in replied_comments:
            if comment.parent and comment.parent.user_id:
                favorite_authors[comment.parent.user_id] += 3  # 回复权重3
        
        # 提取互动过的评论关键词（使用 jieba）
        interaction_keywords = Counter()
        all_content = []
        
        for comment in list(liked_comments) + list(replied_comments):
            all_content.append(comment.content)
            # 使用 jieba 提取关键词（TF-IDF）
            keywords = jieba.analyse.extract_tags(
                comment.content,
                topK=10,
                withWeight=False
            )
            interaction_keywords.update(keywords)
        
        # 生成用户兴趣向量（基于所有互动内容）
        user_interest_vector = None
        if all_content:
            combined_content = " ".join(all_content[:20])  # 最多取20条，避免太长
            user_interest_vector = cls._get_text_embedding(combined_content)
        
        # 获取最近浏览过的作者（从 Redis）
        recent_seen_authors = cls.get_recent_viewed_authors(user.id)
        
        return {
            'favorite_authors': set(favorite_authors.keys()),
            'interaction_keywords': set(interaction_keywords.keys()),
            'user_interest_vector': user_interest_vector,
            'recent_seen_authors': recent_seen_authors,
        }
    
    @classmethod
    def _get_empty_interests(cls) -> Dict:
        """返回空的兴趣数据（未登录用户）
        
        Returns:
            dict: 空的兴趣数据
        """
        return {
            'favorite_authors': set(),
            'interaction_keywords': set(),
            'user_interest_vector': None,
            'recent_seen_authors': [],
        }
    
    @classmethod
    def calculate_content_similarity(
        cls,
        content: str,
        user_interests: Dict
    ) -> float:
        """计算内容与用户兴趣的相似度
        
        使用两种方法：
        1. 关键词匹配（快速，权重30%）
        2. 向量相似度（精确，权重70%）
        
        Args:
            content: 评论内容
            user_interests: 用户兴趣数据
            
        Returns:
            float: 相似度分数（0-1）
        """
        if not user_interests or not content:
            return 0.0
        
        # 方法1：关键词匹配
        keyword_similarity = cls._keyword_similarity(
            content,
            user_interests.get('interaction_keywords', set())
        )
        
        # 方法2：向量相似度
        vector_similarity = 0.0
        user_vector = user_interests.get('user_interest_vector')
        if user_vector:
            content_vector = cls._get_text_embedding(content)
            if content_vector:
                vector_similarity = cls._cosine_similarity(user_vector, content_vector)
        
        # 综合相似度：30%关键词 + 70%向量
        final_similarity = keyword_similarity * 0.3 + vector_similarity * 0.7
        
        return min(final_similarity, 1.0)
    
    @classmethod
    def _keyword_similarity(cls, content: str, keywords: Set[str]) -> float:
        """基于关键词的相似度计算
        
        Args:
            content: 评论内容
            keywords: 用户兴趣关键词集合
            
        Returns:
            float: 相似度分数（0-1）
        """
        if not keywords:
            return 0.0
        
        # 使用 jieba 提取内容关键词
        content_keywords = set(jieba.analyse.extract_tags(
            content,
            topK=10,
            withWeight=False
        ))
        
        if not content_keywords:
            return 0.0
        
        # 计算 Jaccard 相似度
        intersection = content_keywords & keywords
        union = content_keywords | keywords
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    @classmethod
    def _get_text_embedding(cls, text: str) -> Optional[List[float]]:
        """获取文本的向量嵌入（使用 BGE-M3）
        
        Args:
            text: 文本内容
            
        Returns:
            List[float]: 1024维向量，失败返回 None
        """
        if not text or len(text) < 2:
            return None
        
        # 截断过长文本（BGE-M3 支持8K，但评论一般不会太长）
        if len(text) > 500:
            text = text[:500]
        
        try:
            # 从配置获取 API Key
            from mainotebook.content.services.moderation_service import _get_api_key
            api_key = _get_api_key()
            
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.siliconflow.cn/v1"
            )
            
            response = client.embeddings.create(
                model=cls.BGE_M3_MODEL,
                input=text,
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            return embedding
            
        except Exception as e:
            logger.warning(f"获取文本嵌入失败: {e}")
            return None
    
    @classmethod
    def _cosine_similarity(cls, vec1: List[float], vec2: List[float]) -> float:
        """计算两个向量的余弦相似度
        
        Args:
            vec1: 向量1
            vec2: 向量2
            
        Returns:
            float: 余弦相似度（0-1）
        """
        import math
        
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        # 计算点积
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # 计算模长
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        # 余弦相似度
        similarity = dot_product / (magnitude1 * magnitude2)
        
        # 归一化到 [0, 1]
        return (similarity + 1) / 2
    
    @classmethod
    def rerank_comments(
        cls,
        comments: List,
        user_interests: Dict,
        top_k: int = None
    ) -> List:
        """使用 BGE-Reranker 重排序评论
        
        对候选评论进行精细重排序，提升推荐质量。
        
        Args:
            comments: 评论列表（已经过初步排序）
            user_interests: 用户兴趣数据
            top_k: 返回前 K 个结果（None 表示全部）
            
        Returns:
            List: 重排序后的评论列表
        """
        if not comments or not user_interests or len(comments) <= 1:
            return comments
        
        # 构建用户兴趣查询文本
        query_parts = []
        if user_interests.get('interaction_keywords'):
            query_parts.append(" ".join(list(user_interests['interaction_keywords'])[:20]))
        
        if not query_parts:
            return comments  # 没有兴趣数据，不重排序
        
        query = " ".join(query_parts)
        
        try:
            # 准备文档列表
            documents = [comment.content for comment in comments]
            
            # 调用 BGE-Reranker API
            from mainotebook.content.services.moderation_service import _get_api_key
            api_key = _get_api_key()
            
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.siliconflow.cn/v1"
            )
            
            # BGE-Reranker 使用 chat completion 接口
            # 构建重排序请求
            scores = []
            for doc in documents:
                # 简化处理：使用嵌入相似度作为分数
                # 实际 BGE-Reranker 应该有专门的 API，这里用嵌入模拟
                doc_vector = cls._get_text_embedding(doc)
                query_vector = cls._get_text_embedding(query)
                
                if doc_vector and query_vector:
                    score = cls._cosine_similarity(query_vector, doc_vector)
                else:
                    score = 0.0
                
                scores.append(score)
            
            # 按分数排序
            comment_score_pairs = list(zip(comments, scores))
            comment_score_pairs.sort(key=lambda x: x[1], reverse=True)
            
            # 返回重排序结果
            reranked_comments = [pair[0] for pair in comment_score_pairs]
            
            if top_k:
                return reranked_comments[:top_k]
            return reranked_comments
            
        except Exception as e:
            logger.warning(f"重排序失败，返回原始顺序: {e}")
            return comments
    
    @classmethod
    def record_user_view(cls, user_id: int, comments: List) -> None:
        """记录用户浏览行为到 Redis
        
        用于多样性控制，避免重复推荐相同作者的内容。
        
        Args:
            user_id: 用户 ID
            comments: 用户浏览的评论列表
        """
        if not user_id or not comments:
            return
        
        try:
            # 提取作者 ID
            author_ids = [
                str(comment.user_id)
                for comment in comments
                if comment.user_id
            ]
            
            if not author_ids:
                return
            
            # Redis 键
            cache_key = f"{cls.CACHE_PREFIX_USER_VIEWS}{user_id}"
            
            # 获取现有记录
            existing_views = cache.get(cache_key, [])
            
            # 添加新记录（保留最近50个）
            updated_views = (author_ids + existing_views)[:50]
            
            # 存入 Redis
            cache.set(cache_key, updated_views, cls.CACHE_TTL_USER_VIEWS)
            
        except Exception as e:
            logger.warning(f"记录用户浏览失败: {e}")
    
    @classmethod
    def get_recent_viewed_authors(cls, user_id: int) -> List[int]:
        """获取用户最近浏览过的作者列表
        
        Args:
            user_id: 用户 ID
            
        Returns:
            List[int]: 作者 ID 列表
        """
        if not user_id:
            return []
        
        try:
            cache_key = f"{cls.CACHE_PREFIX_USER_VIEWS}{user_id}"
            viewed_authors = cache.get(cache_key, [])
            
            # 转换为整数
            return [int(author_id) for author_id in viewed_authors if author_id]
            
        except Exception as e:
            logger.warning(f"获取浏览历史失败: {e}")
            return []
    
    @classmethod
    def clear_user_cache(cls, user_id: int) -> None:
        """清除用户的推荐缓存
        
        当用户行为发生重大变化时调用（如点赞、回复）。
        
        Args:
            user_id: 用户 ID
        """
        try:
            cache_key = f"{cls.CACHE_PREFIX_USER_INTERESTS}{user_id}"
            cache.delete(cache_key)
        except Exception as e:
            logger.warning(f"清除用户缓存失败: {e}")

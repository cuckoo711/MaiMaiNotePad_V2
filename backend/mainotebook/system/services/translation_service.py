"""
翻译服务

提供文本翻译功能，支持从数据库查询翻译结果。
"""

import logging
from typing import Dict, Optional, List
from django.core.cache import cache
from ..models import Translation

logger = logging.getLogger(__name__)


class TranslationService:
    """翻译服务
    
    提供文本翻译功能，支持缓存和批量翻译。
    """
    
    # 缓存过期时间（秒）
    CACHE_TIMEOUT = 3600  # 1小时
    
    @staticmethod
    def get_translation(
        source_text: str,
        translation_type: str,
        source_language: str = 'en',
        target_language: str = 'zh',
    ) -> Optional[str]:
        """获取单个文本的翻译
        
        从数据库查询翻译结果，支持缓存。
        
        Args:
            source_text: 原文
            translation_type: 翻译类型
            source_language: 源语言，默认为 'en'
            target_language: 目标语言，默认为 'zh'
            
        Returns:
            Optional[str]: 翻译结果，如果未找到则返回 None
        """
        if not source_text or not source_text.strip():
            return None
        
        # 生成缓存键
        cache_key = f"translation:{translation_type}:{source_language}:{target_language}:{source_text}"
        
        # 尝试从缓存获取
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # 从数据库查询
        try:
            translation = Translation.objects.filter(
                source_text=source_text,
                translation_type=translation_type,
                source_language=source_language,
                target_language=target_language,
                status=True
            ).first()
            
            if translation:
                result = translation.translated_text
                # 缓存结果
                cache.set(cache_key, result, TranslationService.CACHE_TIMEOUT)
                return result
            
            # 未找到翻译，缓存 None 避免重复查询
            cache.set(cache_key, None, TranslationService.CACHE_TIMEOUT)
            return None
            
        except Exception as e:
            logger.error(f"查询翻译失败: {e}")
            return None
    
    @staticmethod
    def get_translations_batch(
        source_texts: List[str],
        translation_type: str,
        source_language: str = 'en',
        target_language: str = 'zh',
    ) -> Dict[str, str]:
        """批量获取文本翻译
        
        批量查询翻译结果，提高性能。
        
        Args:
            source_texts: 原文列表
            translation_type: 翻译类型
            source_language: 源语言，默认为 'en'
            target_language: 目标语言，默认为 'zh'
            
        Returns:
            Dict[str, str]: 原文到译文的映射字典
        """
        if not source_texts:
            return {}
        
        # 过滤空文本
        valid_texts = [text for text in source_texts if text and text.strip()]
        if not valid_texts:
            return {}
        
        result = {}
        texts_to_query = []
        
        # 先从缓存获取
        for text in valid_texts:
            cache_key = f"translation:{translation_type}:{source_language}:{target_language}:{text}"
            cached_result = cache.get(cache_key)
            
            if cached_result is not None:
                result[text] = cached_result
            else:
                texts_to_query.append(text)
        
        # 批量查询未缓存的文本
        if texts_to_query:
            try:
                translations = Translation.objects.filter(
                    source_text__in=texts_to_query,
                    translation_type=translation_type,
                    source_language=source_language,
                    target_language=target_language,
                    status=True
                )
                
                for translation in translations:
                    source = translation.source_text
                    translated = translation.translated_text
                    result[source] = translated
                    
                    # 缓存结果
                    cache_key = f"translation:{translation_type}:{source_language}:{target_language}:{source}"
                    cache.set(cache_key, translated, TranslationService.CACHE_TIMEOUT)
                
            except Exception as e:
                logger.error(f"批量查询翻译失败: {e}")
        
        return result
    
    @staticmethod
    def translate_with_fallback(
        source_text: str,
        translation_type: str,
        source_language: str = 'en',
        target_language: str = 'zh',
        show_original: bool = True
    ) -> str:
        """翻译文本，如果未找到翻译则返回原文
        
        Args:
            source_text: 原文
            translation_type: 翻译类型
            source_language: 源语言，默认为 'en'
            target_language: 目标语言，默认为 'zh'
            show_original: 是否在翻译后显示原文，默认为 True
            
        Returns:
            str: 翻译结果，格式为 "原文（译文）" 或 "原文"
        """
        if not source_text or not source_text.strip():
            return source_text
        
        translated = TranslationService.get_translation(
            source_text=source_text,
            translation_type=translation_type,
            source_language=source_language,
            target_language=target_language
        )
        
        if translated:
            if show_original:
                return f"{source_text}（{translated}）"
            else:
                return translated
        
        return source_text
    
    @staticmethod
    def clear_cache(translation_type: Optional[str] = None):
        """清除翻译缓存
        
        Args:
            translation_type: 翻译类型，如果为 None 则清除所有翻译缓存
        """
        if translation_type:
            # 清除特定类型的缓存（需要遍历所有键，性能较差）
            logger.warning("清除特定类型的缓存需要遍历所有键，建议清除所有缓存")
        else:
            # 清除所有缓存
            cache.clear()
            logger.info("已清除所有翻译缓存")

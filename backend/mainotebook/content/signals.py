# -*- coding: utf-8 -*-

"""
内容模块信号处理

处理 PersonaCard 和 KnowledgeBase 的标签统计生命周期同步。
当内容的 is_public 状态或标签列表发生变化时，自动同步标签统计。

**Bug 修复**：标签统计生命周期同步
**需求**：2.1, 2.2, 2.3, 2.4
"""

import logging
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver

from mainotebook.content.models import PersonaCard, KnowledgeBase
from mainotebook.content.services.tag_service import TagService

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=PersonaCard)
def persona_card_pre_save(sender, instance, **kwargs):
    """PersonaCard 保存前处理标签统计同步
    
    当 PersonaCard 的 is_public 状态、is_deleted 状态或标签列表发生变化时，同步更新标签统计。
    
    处理逻辑：
    1. is_public 从 False 变为 True：增加标签统计
    2. is_public 从 True 变为 False：减少标签统计
    3. is_deleted 从 False 变为 True 且 is_public=True：减少标签统计
    4. is_public=True 且标签有变化：同步标签差异
    
    Args:
        sender: 发送信号的模型类
        instance: PersonaCard 实例
        **kwargs: 其他参数
    """
    # 如果是新创建的对象，不处理（创建时的标签统计由 perform_create 处理）
    if instance.pk is None:
        return
    
    try:
        # 获取数据库中的旧对象
        old_instance = PersonaCard.objects.get(pk=instance.pk)
    except PersonaCard.DoesNotExist:
        # 对象不存在，可能是新创建的
        return
    
    old_tags = old_instance.tags
    old_is_public = old_instance.is_public
    old_is_deleted = old_instance.is_deleted
    new_tags = instance.tags
    new_is_public = instance.is_public
    new_is_deleted = instance.is_deleted
    
    # 检查 is_deleted 状态变化（软删除）
    if not old_is_deleted and new_is_deleted:
        # 从 False 变为 True：如果之前是公开的，减少标签统计
        if old_is_public:
            TagService.decrease_tag_usage(old_tags, 'persona')
            logger.info(
                f"人设卡 {instance.id} 已软删除，标签统计已减少: tags={old_tags}"
            )
        return  # 删除操作不需要继续处理其他逻辑
    
    # 检查 is_public 状态变化
    if old_is_public != new_is_public:
        if not old_is_public and new_is_public:
            # 从 False 变为 True：增加标签统计
            TagService.update_tag_usage(new_tags, 'persona')
            logger.info(
                f"人设卡 {instance.id} 从私有变为公开，标签统计已增加: tags={new_tags}"
            )
        elif old_is_public and not new_is_public:
            # 从 True 变为 False：减少标签统计
            TagService.decrease_tag_usage(new_tags, 'persona')
            logger.info(
                f"人设卡 {instance.id} 从公开变为私有，标签统计已减少: tags={new_tags}"
            )
    
    # 如果 is_public=True 且标签有变化：同步标签使用
    if new_is_public and old_tags != new_tags:
        TagService.sync_tag_usage(old_tags, new_tags, 'persona')
        logger.info(
            f"人设卡 {instance.id} 标签已更新，标签统计已同步: "
            f"old_tags={old_tags}, new_tags={new_tags}"
        )


@receiver(pre_save, sender=KnowledgeBase)
def knowledge_base_pre_save(sender, instance, **kwargs):
    """KnowledgeBase 保存前处理标签统计同步
    
    当 KnowledgeBase 的 is_public 状态或标签列表发生变化时，同步更新标签统计。
    
    处理逻辑：
    1. is_public 从 False 变为 True：增加标签统计
    2. is_public 从 True 变为 False：减少标签统计
    3. is_public=True 且标签有变化：同步标签差异
    
    Args:
        sender: 发送信号的模型类
        instance: KnowledgeBase 实例
        **kwargs: 其他参数
    """
    # 如果是新创建的对象，不处理（创建时的标签统计由 perform_create 处理）
    if instance.pk is None:
        return
    
    try:
        # 获取数据库中的旧对象
        old_instance = KnowledgeBase.objects.get(pk=instance.pk)
    except KnowledgeBase.DoesNotExist:
        # 对象不存在，可能是新创建的
        return
    
    old_tags = old_instance.tags
    old_is_public = old_instance.is_public
    new_tags = instance.tags
    new_is_public = instance.is_public
    
    # 检查 is_public 状态变化
    if old_is_public != new_is_public:
        if not old_is_public and new_is_public:
            # 从 False 变为 True：增加标签统计
            TagService.update_tag_usage(new_tags, 'knowledge')
            logger.info(
                f"知识库 {instance.id} 从私有变为公开，标签统计已增加: tags={new_tags}"
            )
        elif old_is_public and not new_is_public:
            # 从 True 变为 False：减少标签统计
            TagService.decrease_tag_usage(new_tags, 'knowledge')
            logger.info(
                f"知识库 {instance.id} 从公开变为私有，标签统计已减少: tags={new_tags}"
            )
    
    # 如果 is_public=True 且标签有变化：同步标签使用
    if new_is_public and old_tags != new_tags:
        TagService.sync_tag_usage(old_tags, new_tags, 'knowledge')
        logger.info(
            f"知识库 {instance.id} 标签已更新，标签统计已同步: "
            f"old_tags={old_tags}, new_tags={new_tags}"
        )


@receiver(post_delete, sender=KnowledgeBase)
def knowledge_base_post_delete(sender, instance, **kwargs):
    """KnowledgeBase 删除后处理标签统计同步
    
    当 KnowledgeBase 被物理删除时，如果之前是公开的，减少标签统计。
    
    Args:
        sender: 发送信号的模型类
        instance: KnowledgeBase 实例
        **kwargs: 其他参数
    """
    # 如果之前是公开的，减少标签统计
    if instance.is_public:
        TagService.decrease_tag_usage(instance.tags, 'knowledge')
        logger.info(
            f"知识库 {instance.id} 已物理删除，标签统计已减少: tags={instance.tags}"
        )

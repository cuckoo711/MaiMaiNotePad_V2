"""AI 审核模型管理视图集

提供 AI 审核模型的增删改查接口，供管理后台动态管理模型配置。
"""

import logging

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from rest_framework.permissions import IsAuthenticated

from dvadmin.utils.viewset import CustomModelViewSet
from mainotebook.utils.serializers import CustomModelSerializer
from mainotebook.content.models import AIModel

logger = logging.getLogger(__name__)

# 防止 signal 递归调用的标志
_recalculating = False


def recalculate_priority() -> None:
    """重新计算所有 AI 模型的优先级

    按参数量（B 数）降序排列，同 B 数按最大上下文长度降序排列，
    然后依次赋值 priority = 0, 1, 2, ...
    每次模型增删改时自动调用，确保 priority 始终反映正确的调度顺序。
    """
    global _recalculating
    if _recalculating:
        return
    _recalculating = True
    try:
        models = AIModel.objects.order_by('-parameter_size', '-max_context_length')
        updates = []
        for idx, obj in enumerate(models):
            if obj.priority != idx:
                obj.priority = idx
                updates.append(obj)
        if updates:
            AIModel.objects.bulk_update(updates, ['priority'])
            logger.info("已重新计算 %d 个模型的优先级", len(updates))
    finally:
        _recalculating = False


@receiver(post_save, sender=AIModel)
def on_ai_model_save(sender, instance, **kwargs):
    """模型保存后重新计算优先级"""
    recalculate_priority()


@receiver(post_delete, sender=AIModel)
def on_ai_model_delete(sender, instance, **kwargs):
    """模型删除后重新计算优先级"""
    recalculate_priority()


class AIModelSerializer(CustomModelSerializer):
    """AI 审核模型序列化器"""

    class Meta:
        model = AIModel
        fields = '__all__'


class AIModelViewSet(CustomModelViewSet):
    """AI 审核模型管理视图集

    提供模型配置的增删改查功能，仅管理员可访问。
    """

    queryset = AIModel.objects.all()
    serializer_class = AIModelSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name', 'provider']
    filterset_fields = ['is_enabled', 'provider']
    ordering_fields = ['priority', 'parameter_size', 'max_context_length', 'create_datetime']
    ordering = ['priority']

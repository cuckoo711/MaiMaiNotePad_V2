"""
AI 审核日志视图集

提供 ModerationLog 的只读列表和详情查看接口，供管理后台使用。
"""

import django_filters
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import SuccessResponse
from mainotebook.utils.serializers import CustomModelSerializer
from mainotebook.content.models import ModerationLog


class ModerationLogFilterSet(django_filters.FilterSet):
    """AI 审核日志过滤器

    为不同字段配置合适的查询方式：
    - 下拉选择字段使用精确匹配
    - 文本输入字段使用模糊匹配
    """

    source = django_filters.CharFilter(lookup_expr='exact')
    decision = django_filters.CharFilter(lookup_expr='exact')
    is_success = django_filters.BooleanFilter()
    model_name = django_filters.CharFilter(lookup_expr='icontains')
    input_text = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = ModerationLog
        fields = ['source', 'decision', 'is_success', 'model_name', 'input_text']


class ModerationLogSerializer(CustomModelSerializer):
    """AI 审核日志序列化器"""

    source_label = serializers.CharField(
        source='get_source_display', read_only=True
    )
    decision_label = serializers.CharField(
        source='get_decision_display', read_only=True
    )
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = ModerationLog
        fields = '__all__'

    def get_user_name(self, obj) -> str:
        """获取触发用户的用户名"""
        if obj.user:
            return obj.user.username or obj.user.name or str(obj.user.id)
        return '-'


class ModerationLogViewSet(CustomModelViewSet):
    """AI 审核日志管理视图集

    只读接口，供管理后台查看 AI 审核调用记录。
    提供列表查询、详情查看和统计汇总功能。
    """

    queryset = ModerationLog.objects.all().order_by('-create_datetime')
    serializer_class = ModerationLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = ModerationLogFilterSet
    ordering_fields = ['create_datetime', 'total_tokens', 'latency_ms']

    @action(methods=['GET'], detail=False, url_path='stats')
    def stats(self, request):
        """获取审核日志统计数据

        返回总调用次数、成功率、Token 消耗等汇总信息。
        """
        from django.db.models import Sum, Avg, Count, Q
        from django.utils import timezone
        from datetime import timedelta

        qs = ModerationLog.objects.all()
        today = timezone.now().date()
        last_30_days = today - timedelta(days=30)

        total_count = qs.count()
        success_count = qs.filter(is_success=True).count()
        today_count = qs.filter(create_datetime__date=today).count()

        # Token 用量统计
        token_stats = qs.aggregate(
            total_tokens_sum=Sum('total_tokens'),
            prompt_tokens_sum=Sum('prompt_tokens'),
            completion_tokens_sum=Sum('completion_tokens'),
            avg_latency=Avg('latency_ms'),
        )

        # 按决策分布
        decision_dist = dict(
            qs.values_list('decision')
            .annotate(count=Count('id'))
            .values_list('decision', 'count')
        )

        # 按来源分布
        source_dist = dict(
            qs.values_list('source')
            .annotate(count=Count('id'))
            .values_list('source', 'count')
        )

        data = {
            'total_count': total_count,
            'success_count': success_count,
            'success_rate': round(success_count / total_count * 100, 1) if total_count else 0,
            'today_count': today_count,
            'total_tokens': token_stats['total_tokens_sum'] or 0,
            'prompt_tokens': token_stats['prompt_tokens_sum'] or 0,
            'completion_tokens': token_stats['completion_tokens_sum'] or 0,
            'avg_latency_ms': round(token_stats['avg_latency'] or 0, 1),
            'decision_distribution': decision_dist,
            'source_distribution': source_dist,
        }
        return SuccessResponse(data=data, msg="获取成功")

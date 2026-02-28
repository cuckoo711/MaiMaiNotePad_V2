"""
AI 内容审核序列化器
"""

from rest_framework import serializers


class ModerationRequestSerializer(serializers.Serializer):
    """审核请求序列化器"""
    
    text = serializers.CharField(
        required=True,
        allow_blank=False,
        help_text="待审核的文本内容"
    )
    text_type = serializers.ChoiceField(
        choices=['comment', 'post', 'title', 'content'],
        default='comment',
        help_text="文本类型"
    )


class ModerationResultSerializer(serializers.Serializer):
    """审核结果序列化器"""
    
    decision = serializers.ChoiceField(
        choices=['true', 'false', 'unknown'],
        help_text="审核决策：true（通过）、false（拒绝）、unknown（不确定）"
    )
    confidence = serializers.FloatField(
        min_value=0.0,
        max_value=1.0,
        help_text="违规置信度（0-1）"
    )
    violation_types = serializers.ListField(
        child=serializers.ChoiceField(choices=['porn', 'politics', 'abuse']),
        help_text="违规类型列表"
    )


class ModerationResponseSerializer(serializers.Serializer):
    """审核响应序列化器"""
    
    success = serializers.BooleanField(default=True)
    result = ModerationResultSerializer()
    message = serializers.CharField(default="审核完成")

"""
审核序列化器

提供内容审核相关的序列化器。
"""

from rest_framework import serializers

from mainotebook.content.models import ReviewReport


class ReviewItemSerializer(serializers.Serializer):
    """审核项序列化器
    
    用于待审核列表展示。
    将知识库和人设卡统一序列化为审核项。
    """
    
    id = serializers.UUIDField(
        help_text="内容 ID"
    )
    name = serializers.CharField(
        help_text="内容名称"
    )
    description = serializers.CharField(
        help_text="内容描述"
    )
    content_type = serializers.CharField(
        help_text="内容类型：knowledge（知识库）或 persona（人设卡）"
    )
    uploader_id = serializers.UUIDField(
        help_text="上传者 ID"
    )
    uploader_name = serializers.CharField(
        help_text="上传者名称"
    )
    create_datetime = serializers.DateTimeField(
        help_text="创建时间"
    )
    tags = serializers.CharField(
        allow_null=True,
        help_text="标签"
    )
    file_count = serializers.IntegerField(
        help_text="文件数量"
    )
    ai_review_decision = serializers.CharField(
        allow_null=True,
        required=False,
        help_text="AI 审核决策：auto_approved、auto_rejected、pending_manual 或 null（未审核）"
    )


class ReviewActionSerializer(serializers.Serializer):
    """审核操作序列化器
    
    用于审核操作（批准、拒绝、退回）的请求数据验证。
    """
    
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="审核原因或备注（拒绝时必填）"
    )
    
    def validate(self, attrs):
        """验证审核操作数据
        
        Args:
            attrs: 待验证的属性字典
            
        Returns:
            dict: 验证后的属性字典
            
        Raises:
            ValidationError: 当拒绝操作缺少原因时
        """
        action = self.context.get('action')
        reason = attrs.get('reason', '')
        
        # 拒绝操作必须提供原因
        if action == 'reject' and not reason:
            raise serializers.ValidationError({
                'reason': "拒绝内容时必须提供原因"
            })
        
        return attrs


class ReviewHistorySerializer(serializers.Serializer):
    """审核历史序列化器
    
    用于审核历史记录展示。
    显示审核员处理过的所有审核记录。
    """
    
    id = serializers.UUIDField(
        help_text="内容 ID"
    )
    name = serializers.CharField(
        help_text="内容名称"
    )
    content_type = serializers.CharField(
        help_text="内容类型：knowledge（知识库）或 persona（人设卡）"
    )
    action = serializers.CharField(
        help_text="审核操作：approve（批准）、reject（拒绝）、return（退回）"
    )
    reason = serializers.CharField(
        allow_null=True,
        help_text="审核原因或备注"
    )
    reviewer_name = serializers.CharField(
        help_text="审核员名称"
    )
    review_datetime = serializers.DateTimeField(
        help_text="审核时间"
    )

class BatchReviewSerializer(serializers.Serializer):
    """批量审核操作序列化器

    用于批量审核通过和批量审核拒绝的请求数据验证。
    支持一次性对多条内容执行相同审核操作。
    """

    ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="内容 ID 列表"
    )
    content_type = serializers.ChoiceField(
        choices=['knowledge', 'persona'],
        help_text="内容类型：knowledge（知识库）或 persona（人设卡）"
    )
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="审核原因（批量拒绝时必填）"
    )

    def validate(self, attrs):
        """验证批量审核操作数据

        当操作为批量拒绝时，reason 字段为必填。

        Args:
            attrs: 待验证的属性字典

        Returns:
            dict: 验证后的属性字典

        Raises:
            ValidationError: 当批量拒绝操作缺少原因时
        """
        action = self.context.get('action')
        reason = attrs.get('reason', '')

        # 批量拒绝操作必须提供原因
        if action == 'batch_reject' and not reason:
            raise serializers.ValidationError({
                'reason': "拒绝内容时必须提供原因"
            })

        return attrs



class AIReviewRequestSerializer(serializers.Serializer):
    """AI 审核请求序列化器

    用于单条 AI 审核请求的数据验证。
    管理员在审核页面对单条内容触发 AI 审核时使用。
    """

    content_type = serializers.ChoiceField(
        choices=['knowledge', 'persona'],
        help_text="内容类型：knowledge（知识库）或 persona（人设卡）"
    )


class BatchAIReviewRequestSerializer(serializers.Serializer):
    """批量 AI 审核请求序列化器

    用于批量 AI 审核请求的数据验证。
    管理员在审核页面选择多条内容触发批量 AI 审核时使用。
    """

    ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="内容 ID 列表"
    )
    content_type = serializers.ChoiceField(
        choices=['knowledge', 'persona'],
        help_text="内容类型：knowledge（知识库）或 persona（人设卡）"
    )


class ReviewReportSerializer(serializers.ModelSerializer):
    """AI 审核报告序列化器

    用于序列化 ReviewReport 模型数据。
    管理员查看 AI 审核报告详情时使用。
    """

    class Meta:
        model = ReviewReport
        fields = [
            'id', 'content_id', 'content_type', 'content_name',
            'decision', 'final_confidence', 'violation_types',
            'report_data', 'create_datetime',
        ]

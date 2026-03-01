"""
Content 应用数据模型

包含从 FastAPI 项目迁移过来的所有内容相关模型。
"""

import uuid
from django.db import models
from mainotebook.utils.models import CoreModel, table_prefix
from mainotebook.system.models import Users


class KnowledgeBase(CoreModel):
    """知识库模型
    
    存储用户上传的知识库内容，包括名称、描述、文件等信息。
    支持公开/私有状态、审核流程、版本管理。
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="知识库ID",
        help_text="知识库唯一标识"
    )
    name = models.CharField(
        max_length=200,
        verbose_name="知识库名称",
        help_text="知识库名称"
    )
    description = models.TextField(
        verbose_name="知识库描述",
        help_text="知识库描述"
    )
    uploader = models.ForeignKey(
        to=Users,
        on_delete=models.PROTECT,
        db_constraint=False,
        related_name="uploaded_knowledge_bases",
        verbose_name="上传者",
        help_text="上传者"
    )
    copyright_owner = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="版权所有者",
        help_text="版权所有者"
    )
    content = models.TextField(
        null=True,
        blank=True,
        verbose_name="内容",
        help_text="知识库文本内容"
    )
    tags = models.TextField(
        null=True,
        blank=True,
        verbose_name="标签",
        help_text="标签，多个标签用逗号分隔"
    )
    star_count = models.IntegerField(
        default=0,
        verbose_name="收藏数",
        help_text="收藏数"
    )
    downloads = models.IntegerField(
        default=0,
        verbose_name="下载次数",
        help_text="下载次数"
    )
    base_path = models.TextField(
        default="[]",
        verbose_name="基础路径",
        help_text="基础路径，JSON 数组格式"
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name="是否公开",
        help_text="是否公开"
    )
    is_pending = models.BooleanField(
        default=True,
        verbose_name="是否待审核",
        help_text="是否待审核"
    )
    rejection_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name="拒绝原因",
        help_text="审核拒绝原因"
    )
    
    def to_dict(self) -> dict:
        """转换为字典格式
        
        Returns:
            dict: 包含所有字段的字典
        """
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'uploader_id': self.uploader_id,
            'copyright_owner': self.copyright_owner,
            'content': self.content,
            'tags': self.tags,
            'star_count': self.star_count,
            'downloads': self.downloads,
            'base_path': self.base_path,
            'is_public': self.is_public,
            'is_pending': self.is_pending,
            'rejection_reason': self.rejection_reason,
            'created_at': self.create_datetime.isoformat() if self.create_datetime else None,
            'updated_at': self.update_datetime.isoformat() if self.update_datetime else None,
        }
    
    class Meta:
        db_table = table_prefix + "content_knowledge_base"
        verbose_name = "知识库"
        verbose_name_plural = verbose_name
        ordering = ("-create_datetime",)
        indexes = [
            models.Index(fields=['uploader']),
            models.Index(fields=['is_public']),
            models.Index(fields=['is_pending']),
            models.Index(fields=['star_count']),
            models.Index(fields=['create_datetime']),
            models.Index(fields=['update_datetime']),
        ]
    
    def __str__(self) -> str:
        return f"{self.name}"


class KnowledgeBaseFile(CoreModel):
    """知识库文件模型
    
    存储知识库关联的文件信息，包括文件名、路径、类型、大小等。
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="文件ID",
        help_text="文件唯一标识"
    )
    knowledge_base = models.ForeignKey(
        to=KnowledgeBase,
        on_delete=models.CASCADE,
        db_constraint=False,
        related_name="files",
        verbose_name="关联知识库",
        help_text="关联知识库"
    )
    file_name = models.CharField(
        max_length=255,
        verbose_name="文件名",
        help_text="存储的文件名"
    )
    original_name = models.CharField(
        max_length=255,
        verbose_name="原始文件名",
        help_text="用户上传时的原始文件名"
    )
    file_path = models.CharField(
        max_length=500,
        verbose_name="文件路径",
        help_text="文件存储路径"
    )
    file_type = models.CharField(
        max_length=100,
        verbose_name="文件类型",
        help_text="文件 MIME 类型"
    )
    file_size = models.BigIntegerField(
        default=0,
        verbose_name="文件大小",
        help_text="文件大小（字节）"
    )
    
    class Meta:
        db_table = table_prefix + "content_knowledge_base_file"
        verbose_name = "知识库文件"
        verbose_name_plural = verbose_name
        ordering = ("-create_datetime",)
        indexes = [
            models.Index(fields=['knowledge_base']),
            models.Index(fields=['file_type']),
            models.Index(fields=['file_size']),
            models.Index(fields=['create_datetime']),
            models.Index(fields=['update_datetime']),
        ]
    
    def __str__(self) -> str:
        return f"{self.original_name} ({self.file_type})"


class PersonaCard(CoreModel):
    """人设卡模型
    
    存储用户上传的人设卡内容，结构与知识库模型相同。
    支持公开/私有状态、审核流程、版本管理。
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="人设卡ID",
        help_text="人设卡唯一标识"
    )
    name = models.CharField(
        max_length=200,
        verbose_name="人设卡名称",
        help_text="人设卡名称"
    )
    description = models.TextField(
        verbose_name="人设卡描述",
        help_text="人设卡描述"
    )
    uploader = models.ForeignKey(
        to=Users,
        on_delete=models.PROTECT,
        db_constraint=False,
        related_name="uploaded_persona_cards",
        verbose_name="上传者",
        help_text="上传者"
    )
    copyright_owner = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="版权所有者",
        help_text="版权所有者"
    )
    content = models.TextField(
        null=True,
        blank=True,
        verbose_name="内容",
        help_text="人设卡文本内容"
    )
    tags = models.TextField(
        null=True,
        blank=True,
        verbose_name="标签",
        help_text="标签，多个标签用逗号分隔"
    )
    star_count = models.IntegerField(
        default=0,
        verbose_name="收藏数",
        help_text="收藏数"
    )
    downloads = models.IntegerField(
        default=0,
        verbose_name="下载次数",
        help_text="下载次数"
    )
    base_path = models.TextField(
        default="[]",
        verbose_name="基础路径",
        help_text="基础路径，JSON 数组格式"
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name="是否公开",
        help_text="是否公开"
    )
    is_pending = models.BooleanField(
        default=True,
        verbose_name="是否待审核",
        help_text="是否待审核"
    )
    rejection_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name="拒绝原因",
        help_text="审核拒绝原因"
    )
    version = models.CharField(
        max_length=50,
        default="1.0",
        verbose_name="版本号",
        help_text="版本号"
    )
    
    def to_dict(self) -> dict:
        """转换为字典格式
        
        Returns:
            dict: 包含所有字段的字典
        """
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'uploader_id': self.uploader_id,
            'copyright_owner': self.copyright_owner,
            'content': self.content,
            'tags': self.tags,
            'star_count': self.star_count,
            'downloads': self.downloads,
            'base_path': self.base_path,
            'is_public': self.is_public,
            'is_pending': self.is_pending,
            'rejection_reason': self.rejection_reason,
            'version': self.version,
            'created_at': self.create_datetime.isoformat() if self.create_datetime else None,
            'updated_at': self.update_datetime.isoformat() if self.update_datetime else None,
        }
    
    class Meta:
        db_table = table_prefix + "content_persona_card"
        verbose_name = "人设卡"
        verbose_name_plural = verbose_name
        ordering = ("-create_datetime",)
        indexes = [
            models.Index(fields=['uploader']),
            models.Index(fields=['is_public']),
            models.Index(fields=['is_pending']),
            models.Index(fields=['star_count']),
            models.Index(fields=['create_datetime']),
            models.Index(fields=['update_datetime']),
        ]
    
    def __str__(self) -> str:
        return f"{self.name} (v{self.version})"


class PersonaCardFile(CoreModel):
    """人设卡文件模型
    
    存储人设卡关联的文件信息，包括文件名、路径、类型、大小等。
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="文件ID",
        help_text="文件唯一标识"
    )
    persona_card = models.ForeignKey(
        to=PersonaCard,
        on_delete=models.CASCADE,
        db_constraint=False,
        related_name="files",
        verbose_name="关联人设卡",
        help_text="关联人设卡"
    )
    file_name = models.CharField(
        max_length=255,
        verbose_name="文件名",
        help_text="存储的文件名"
    )
    original_name = models.CharField(
        max_length=255,
        verbose_name="原始文件名",
        help_text="用户上传时的原始文件名"
    )
    file_path = models.CharField(
        max_length=500,
        verbose_name="文件路径",
        help_text="文件存储路径"
    )
    file_type = models.CharField(
        max_length=100,
        verbose_name="文件类型",
        help_text="文件 MIME 类型"
    )
    file_size = models.BigIntegerField(
        default=0,
        verbose_name="文件大小",
        help_text="文件大小（字节）"
    )
    
    class Meta:
        db_table = table_prefix + "content_persona_card_file"
        verbose_name = "人设卡文件"
        verbose_name_plural = verbose_name
        ordering = ("-create_datetime",)
        indexes = [
            models.Index(fields=['persona_card']),
            models.Index(fields=['file_type']),
            models.Index(fields=['file_size']),
            models.Index(fields=['create_datetime']),
            models.Index(fields=['update_datetime']),
        ]
    
    def __str__(self) -> str:
        return f"{self.original_name} ({self.file_type})"


class Comment(CoreModel):
    """评论模型
    
    支持对知识库和人设卡的评论，支持嵌套回复（通过 parent 字段）。
    包含点赞/点踩计数、软删除功能。
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="评论ID",
        help_text="评论唯一标识"
    )
    user = models.ForeignKey(
        to=Users,
        on_delete=models.PROTECT,
        db_constraint=False,
        related_name="comments",
        verbose_name="评论用户",
        help_text="评论用户"
    )
    target_id = models.CharField(
        max_length=36,
        verbose_name="目标ID",
        help_text="评论目标的 UUID"
    )
    TARGET_TYPE_CHOICES = (
        ('knowledge', '知识库'),
        ('persona', '人设卡'),
    )
    target_type = models.CharField(
        max_length=20,
        choices=TARGET_TYPE_CHOICES,
        verbose_name="目标类型",
        help_text="评论目标类型"
    )
    parent = models.ForeignKey(
        to='self',
        on_delete=models.CASCADE,
        db_constraint=False,
        null=True,
        blank=True,
        related_name="replies",
        verbose_name="父评论",
        help_text="父评论，用于嵌套回复"
    )
    reply_to = models.ForeignKey(
        to='self',
        on_delete=models.SET_NULL,
        db_constraint=False,
        null=True,
        blank=True,
        related_name="mentioned_in",
        verbose_name="回复目标评论",
        help_text="回复的具体评论（用于显示'回复 @xxx'）"
    )
    content = models.TextField(
        verbose_name="评论内容",
        help_text="评论内容"
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="是否已删除",
        help_text="软删除标记"
    )
    MODERATION_STATUS_CHOICES = (
        ('approved', 'AI 审核通过'),
        ('rejected', 'AI 审核拒绝'),
        ('uncertain', 'AI 审核不确定'),
    )
    moderation_status = models.CharField(
        max_length=20,
        choices=MODERATION_STATUS_CHOICES,
        default='approved',
        verbose_name="审核状态",
        help_text="AI 内容审核状态"
    )
    moderation_detail = models.JSONField(
        null=True,
        blank=True,
        verbose_name="审核详情",
        help_text="AI 审核返回的详细信息（JSON 格式）"
    )
    like_count = models.IntegerField(
        default=0,
        verbose_name="点赞数",
        help_text="点赞数"
    )
    dislike_count = models.IntegerField(
        default=0,
        verbose_name="点踩数",
        help_text="点踩数"
    )
    
    class Meta:
        db_table = table_prefix + "content_comment"
        verbose_name = "评论"
        verbose_name_plural = verbose_name
        ordering = ("-create_datetime",)
        indexes = [
            models.Index(fields=['target_id', 'target_type']),
            models.Index(fields=['user']),
            models.Index(fields=['parent']),
            models.Index(fields=['create_datetime']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user.username} 的评论: {self.content[:50]}"


class CommentReaction(CoreModel):
    """评论反应模型
    
    记录用户对评论的点赞或点踩行为。
    每个用户对每条评论只能有一个反应（通过唯一约束保证）。
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="反应ID",
        help_text="反应唯一标识"
    )
    user = models.ForeignKey(
        to=Users,
        on_delete=models.CASCADE,
        db_constraint=False,
        related_name="comment_reactions",
        verbose_name="用户",
        help_text="反应用户"
    )
    comment = models.ForeignKey(
        to=Comment,
        on_delete=models.CASCADE,
        db_constraint=False,
        related_name="reactions",
        verbose_name="评论",
        help_text="关联评论"
    )
    REACTION_TYPE_CHOICES = (
        ('like', '点赞'),
        ('dislike', '点踩'),
    )
    reaction_type = models.CharField(
        max_length=10,
        choices=REACTION_TYPE_CHOICES,
        verbose_name="反应类型",
        help_text="反应类型"
    )
    
    class Meta:
        db_table = table_prefix + "content_comment_reaction"
        verbose_name = "评论反应"
        verbose_name_plural = verbose_name
        ordering = ("-create_datetime",)
        indexes = [
            models.Index(fields=['comment']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'comment'],
                name='unique_user_comment_reaction'
            )
        ]
    
    def __str__(self) -> str:
        return f"{self.user.username} {self.get_reaction_type_display()} 评论 {self.comment_id}"


class StarRecord(CoreModel):
    """收藏记录模型
    
    记录用户对知识库或人设卡的收藏行为。
    每个用户对每个目标只能收藏一次（通过唯一约束保证）。
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="收藏ID",
        help_text="收藏记录唯一标识"
    )
    user = models.ForeignKey(
        to=Users,
        on_delete=models.CASCADE,
        db_constraint=False,
        related_name="star_records",
        verbose_name="用户",
        help_text="收藏用户"
    )
    target_id = models.CharField(
        max_length=36,
        verbose_name="目标ID",
        help_text="收藏目标的 UUID"
    )
    TARGET_TYPE_CHOICES = (
        ('knowledge', '知识库'),
        ('persona', '人设卡'),
    )
    target_type = models.CharField(
        max_length=20,
        choices=TARGET_TYPE_CHOICES,
        verbose_name="目标类型",
        help_text="收藏目标类型"
    )
    
    class Meta:
        db_table = table_prefix + "content_star_record"
        verbose_name = "收藏记录"
        verbose_name_plural = verbose_name
        ordering = ("-create_datetime",)
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['target_id']),
            models.Index(fields=['target_type']),
            models.Index(fields=['create_datetime']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'target_id', 'target_type'],
                name='unique_user_target_star'
            )
        ]
    
    def __str__(self) -> str:
        return f"{self.user.username} 收藏了 {self.get_target_type_display()} {self.target_id}"


class EmailVerification(CoreModel):
    """邮箱验证模型
    
    存储邮箱验证码，用于用户注册、找回密码等场景。
    包含验证码、使用状态、过期时间等信息。
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="验证ID",
        help_text="验证记录唯一标识"
    )
    email = models.EmailField(
        max_length=255,
        verbose_name="邮箱地址",
        help_text="邮箱地址"
    )
    code = models.CharField(
        max_length=10,
        verbose_name="验证码",
        help_text="验证码"
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name="是否已使用",
        help_text="是否已使用"
    )
    expires_at = models.DateTimeField(
        verbose_name="过期时间",
        help_text="验证码过期时间"
    )
    
    class Meta:
        db_table = table_prefix + "content_email_verification"
        verbose_name = "邮箱验证"
        verbose_name_plural = verbose_name
        ordering = ("-create_datetime",)
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['code']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.email} 的验证码: {self.code}"


class UploadRecord(CoreModel):
    """上传记录模型
    
    记录用户的上传行为和审核状态。
    包含上传者、目标信息、审核状态等。
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="上传记录ID",
        help_text="上传记录唯一标识"
    )
    uploader = models.ForeignKey(
        to=Users,
        on_delete=models.PROTECT,
        db_constraint=False,
        related_name="upload_records",
        verbose_name="上传者",
        help_text="上传者"
    )
    target_id = models.CharField(
        max_length=36,
        verbose_name="目标ID",
        help_text="上传目标的 UUID"
    )
    TARGET_TYPE_CHOICES = (
        ('knowledge', '知识库'),
        ('persona', '人设卡'),
    )
    target_type = models.CharField(
        max_length=20,
        choices=TARGET_TYPE_CHOICES,
        verbose_name="目标类型",
        help_text="上传目标类型"
    )
    name = models.CharField(
        max_length=200,
        verbose_name="名称",
        help_text="上传内容名称"
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name="描述",
        help_text="上传内容描述"
    )
    STATUS_CHOICES = (
        ('pending', '待审核'),
        ('approved', '已通过'),
        ('rejected', '已拒绝'),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="审核状态",
        help_text="审核状态"
    )
    
    class Meta:
        db_table = table_prefix + "content_upload_record"
        verbose_name = "上传记录"
        verbose_name_plural = verbose_name
        ordering = ("-create_datetime",)
        indexes = [
            models.Index(fields=['uploader']),
            models.Index(fields=['target_id']),
            models.Index(fields=['target_type']),
            models.Index(fields=['status']),
            models.Index(fields=['create_datetime']),
        ]
    
    def __str__(self) -> str:
        return f"{self.uploader.username} 上传了 {self.name} ({self.get_status_display()})"


class DownloadRecord(CoreModel):
    """下载记录模型
    
    记录知识库和人设卡的下载行为，用于统计下载次数。
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="下载记录ID",
        help_text="下载记录唯一标识"
    )
    target_id = models.CharField(
        max_length=36,
        verbose_name="目标ID",
        help_text="下载目标的 UUID"
    )
    TARGET_TYPE_CHOICES = (
        ('knowledge', '知识库'),
        ('persona', '人设卡'),
    )
    target_type = models.CharField(
        max_length=20,
        choices=TARGET_TYPE_CHOICES,
        verbose_name="目标类型",
        help_text="下载目标类型"
    )
    
    class Meta:
        db_table = table_prefix + "content_download_record"
        verbose_name = "下载记录"
        verbose_name_plural = verbose_name
        ordering = ("-create_datetime",)
        indexes = [
            models.Index(fields=['target_id']),
            models.Index(fields=['target_type']),
            models.Index(fields=['create_datetime']),
        ]
    
    def __str__(self) -> str:
        return f"下载 {self.get_target_type_display()} {self.target_id}"


class ReviewReport(CoreModel):
    """AI 审核报告模型

    存储 AI 自动审核的详细结果，以 JSON 格式保存结构化数据。
    每次 AI 审核完成后（无论通过、拒绝还是待人工复核）都会生成一份报告。
    """

    CONTENT_TYPE_CHOICES = (
        ('knowledge', '知识库'),
        ('persona', '人设卡'),
    )

    DECISION_CHOICES = (
        ('pending_ai', 'AI 审核中'),
        ('auto_approved', '自动通过'),
        ('auto_rejected', '自动拒绝'),
        ('pending_manual', '待人工复核'),
        ('error', '审核异常'),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="报告ID",
        help_text="审核报告唯一标识"
    )
    content_id = models.UUIDField(
        verbose_name="内容ID",
        help_text="关联的知识库或人设卡 ID"
    )
    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPE_CHOICES,
        verbose_name="内容类型"
    )
    content_name = models.CharField(
        max_length=200,
        verbose_name="内容名称"
    )
    decision = models.CharField(
        max_length=20,
        choices=DECISION_CHOICES,
        verbose_name="审核决策"
    )
    final_confidence = models.FloatField(
        verbose_name="最终置信度"
    )
    violation_types = models.JSONField(
        default=list,
        verbose_name="违规类型汇总"
    )
    report_data = models.JSONField(
        verbose_name="报告详细数据",
        help_text="包含各审核部分的详细结果，JSON 格式"
    )

    class Meta:
        db_table = table_prefix + "content_review_report"
        verbose_name = "AI 审核报告"
        verbose_name_plural = verbose_name
        ordering = ("-create_datetime",)
        indexes = [
            models.Index(fields=['content_id']),
            models.Index(fields=['content_type']),
            models.Index(fields=['decision']),
            models.Index(fields=['create_datetime']),
        ]

    def __str__(self) -> str:
        """返回审核报告的字符串表示"""
        return f"[{self.get_decision_display()}] {self.content_name} ({self.get_content_type_display()})"

    def to_readable_text(self) -> str:
        """将审核报告渲染为可读文本格式，用于站内信展示

        Returns:
            str: 格式化的审核报告文本
        """
        # 决策结果映射为中文描述
        decision_map = {
            'pending_ai': '⏳ AI 审核中',
            'auto_approved': '✅ 自动通过',
            'auto_rejected': '❌ 自动拒绝',
            'pending_manual': '⏳ 待人工复核',
            'error': '⚠️ 审核异常',
        }
        decision_text = decision_map.get(self.decision, self.decision)

        lines = [
            f"📋 AI 审核报告",
            f"{'=' * 40}",
            f"内容名称：{self.content_name}",
            f"内容类型：{self.get_content_type_display()}",
            f"审核决策：{decision_text}",
            f"最终置信度：{self.final_confidence:.2f}",
        ]

        # 违规类型
        if self.violation_types:
            violation_map = {
                'porn': '色情',
                'politics': '涉政',
                'abuse': '辱骂',
                'violence': '暴力',
                'spam': '垃圾信息',
                'illegal': '违法',
            }
            violation_labels = [violation_map.get(v, v) for v in self.violation_types]
            lines.append(f"违规类型：{', '.join(violation_labels)}")
        else:
            lines.append("违规类型：无")

        # 各审核部分详情
        parts = self.report_data.get('parts', []) if isinstance(self.report_data, dict) else []
        if parts:
            lines.append(f"\n{'─' * 40}")
            lines.append("📝 审核详情")
            for part in parts:
                part_name = part.get('part_name', '未知')
                part_confidence = part.get('confidence', 0)
                part_violations = part.get('violation_types', [])
                violation_labels = [violation_map.get(v, v) for v in part_violations] if part_violations else ['无']
                lines.append(f"\n  ▸ {part_name}")
                lines.append(f"    置信度：{part_confidence:.2f}")
                lines.append(f"    违规类型：{', '.join(violation_labels)}")

                # 违规片段
                flagged = part.get('flagged_content', '')
                if flagged:
                    lines.append(f"    违规片段：{flagged}")

                # 分段详情
                segments = part.get('segments', [])
                if segments:
                    lines.append(f"    分段审核：")
                    for seg in segments:
                        seg_index = seg.get('segment_index', '?')
                        seg_summary = seg.get('text_summary', '')
                        seg_confidence = seg.get('confidence', 0)
                        seg_violations = seg.get('violation_types', [])
                        seg_violation_labels = [violation_map.get(v, v) for v in seg_violations] if seg_violations else ['无']
                        lines.append(f"      第 {seg_index} 段：置信度 {seg_confidence:.2f}，违规类型：{', '.join(seg_violation_labels)}")
                        if seg_summary:
                            lines.append(f"        摘要：{seg_summary}")
                        seg_flagged = seg.get('flagged_content', '')
                        if seg_flagged:
                            lines.append(f"        违规片段：{seg_flagged}")

        lines.append(f"\n{'=' * 40}")
        return "\n".join(lines)


class AIModel(CoreModel):
    """AI 审核模型配置

    存储可用于内容审核的 AI 模型信息，支持在管理后台动态管理。
    ModelPool 从此表读取启用的模型列表，按优先级排序后进行负载均衡调度。
    """

    name = models.CharField(
        max_length=200,
        unique=True,
        verbose_name="模型名称",
        help_text="模型全称，如 deepseek-ai/DeepSeek-R1-0528-Qwen3-8B"
    )
    provider = models.CharField(
        max_length=50,
        default="siliconflow",
        verbose_name="API 提供商",
        help_text="API 服务提供商标识，如 siliconflow"
    )
    parameter_size = models.FloatField(
        default=7.0,
        verbose_name="参数量(B)",
        help_text="模型参数量，单位为十亿（B），如 7.0 表示 7B"
    )
    max_context_length = models.IntegerField(
        default=32000,
        verbose_name="最大上下文长度",
        help_text="模型支持的最大上下文 token 数"
    )
    rpm_limit = models.IntegerField(
        default=1000,
        verbose_name="RPM 限制",
        help_text="每分钟最大请求数（Requests Per Minute）"
    )
    tpm_limit = models.IntegerField(
        default=50000,
        verbose_name="TPM 限制",
        help_text="每分钟最大 Token 数（Tokens Per Minute）"
    )
    priority = models.IntegerField(
        default=0,
        verbose_name="优先级",
        help_text="调度优先级，数值越小优先级越高（0 为最高）"
    )
    is_enabled = models.BooleanField(
        default=True,
        verbose_name="是否启用",
        help_text="是否参与负载均衡调度"
    )
    cooldown_seconds = models.IntegerField(
        default=65,
        verbose_name="限速冷却时间(秒)",
        help_text="触发 429 限速后的冷却等待时间"
    )

    class Meta:
        db_table = table_prefix + "content_ai_model"
        verbose_name = "AI 审核模型"
        verbose_name_plural = verbose_name
        ordering = ("priority", "-parameter_size", "-max_context_length")

    def __str__(self) -> str:
        return f"{self.name} ({self.parameter_size}B, {self.max_context_length // 1000}k)"


class ModerationLog(CoreModel):
    """AI 审核操作日志模型

    记录每一次 AI 审核 API 调用的详细信息，用于统计看板、成本分析和审计追踪。
    包含 token 用量、模型信息、审核结果、耗时等关键指标。
    """

    # ==================== 审核来源 ====================
    SOURCE_CHOICES = (
        ('comment', '评论审核'),
        ('knowledge', '知识库审核'),
        ('persona', '人设卡审核'),
        ('knowledge_file', '知识库文件审核'),
    )

    source = models.CharField(
        max_length=30,
        choices=SOURCE_CHOICES,
        verbose_name="审核来源",
        help_text="触发审核的业务场景"
    )
    content_id = models.CharField(
        max_length=36,
        null=True,
        blank=True,
        verbose_name="关联内容ID",
        help_text="关联的评论/知识库/人设卡 ID"
    )
    user = models.ForeignKey(
        to=Users,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_constraint=False,
        related_name="moderation_logs",
        verbose_name="触发用户",
        help_text="触发审核操作的用户"
    )

    # ==================== 模型信息 ====================
    model_name = models.CharField(
        max_length=100,
        verbose_name="模型名称",
        help_text="调用的 AI 模型名称，如 Qwen/Qwen3-8B"
    )
    api_provider = models.CharField(
        max_length=50,
        default="siliconflow",
        verbose_name="API 提供商",
        help_text="API 服务提供商标识"
    )
    temperature = models.FloatField(
        default=0.1,
        verbose_name="温度参数",
        help_text="模型推理温度参数"
    )

    # ==================== 审核内容 ====================
    text_type = models.CharField(
        max_length=30,
        verbose_name="文本类型",
        help_text="审核的文本类型（comment/post/title/content/knowledge/persona）"
    )
    input_text = models.TextField(
        verbose_name="审核输入文本",
        help_text="提交给 AI 审核的原始文本内容"
    )
    input_text_length = models.IntegerField(
        default=0,
        verbose_name="输入文本长度",
        help_text="输入文本的字符数"
    )

    # ==================== Token 用量 ====================
    prompt_tokens = models.IntegerField(
        default=0,
        verbose_name="提示词 Token 数",
        help_text="系统提示词 + 用户输入消耗的 Token 数"
    )
    completion_tokens = models.IntegerField(
        default=0,
        verbose_name="生成 Token 数",
        help_text="模型生成输出消耗的 Token 数"
    )
    total_tokens = models.IntegerField(
        default=0,
        verbose_name="总 Token 数",
        help_text="本次调用消耗的总 Token 数"
    )

    # ==================== 审核结果 ====================
    DECISION_CHOICES = (
        ('true', '通过'),
        ('false', '拒绝'),
        ('unknown', '不确定'),
        ('error', '调用异常'),
    )

    decision = models.CharField(
        max_length=10,
        choices=DECISION_CHOICES,
        verbose_name="审核决策",
        help_text="AI 返回的审核决策"
    )
    confidence = models.FloatField(
        default=0.0,
        verbose_name="置信度",
        help_text="AI 返回的违规置信度（0~1）"
    )
    violation_types = models.JSONField(
        default=list,
        verbose_name="违规类型",
        help_text="AI 检测到的违规类型列表，如 ['porn', 'abuse']"
    )
    raw_output = models.TextField(
        null=True,
        blank=True,
        verbose_name="模型原始输出",
        help_text="AI 模型返回的原始文本（用于调试和审计）"
    )

    # ==================== 性能指标 ====================
    latency_ms = models.IntegerField(
        default=0,
        verbose_name="响应耗时(ms)",
        help_text="从发起 API 请求到收到响应的耗时（毫秒）"
    )
    is_success = models.BooleanField(
        default=True,
        verbose_name="是否调用成功",
        help_text="API 调用是否成功（False 表示异常/超时）"
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name="错误信息",
        help_text="调用失败时的错误信息"
    )

    class Meta:
        db_table = table_prefix + "content_moderation_log"
        verbose_name = "AI 审核日志"
        verbose_name_plural = verbose_name
        ordering = ("-create_datetime",)
        indexes = [
            models.Index(fields=['source']),
            models.Index(fields=['decision']),
            models.Index(fields=['model_name']),
            models.Index(fields=['user']),
            models.Index(fields=['is_success']),
            models.Index(fields=['create_datetime']),
            models.Index(fields=['content_id']),
        ]

    def __str__(self) -> str:
        return f"[{self.get_source_display()}] {self.get_decision_display()} - {self.input_text[:30]}"


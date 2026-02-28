"""
Content 应用 Django Admin 配置

配置后台管理界面，用于管理内容相关模型。

注意：当前项目未启用 django.contrib.admin 应用。
如需使用 Admin 功能，请在 settings.py 的 INSTALLED_APPS 中添加 'django.contrib.admin'。
"""

# 尝试导入 Django Admin，如果未启用则跳过
try:
    from django.contrib import admin
    from django.apps import apps
    
    # 检查 admin 应用是否已注册
    try:
        apps.get_app_config('admin')
        ADMIN_ENABLED = True
    except LookupError:
        ADMIN_ENABLED = False
except ImportError:
    ADMIN_ENABLED = False


if ADMIN_ENABLED:
    from .models import (
        KnowledgeBase, 
        KnowledgeBaseFile,
        PersonaCard, 
        PersonaCardFile,
        Comment,
        CommentReaction,
        StarRecord,
        EmailVerification,
        UploadRecord,
        DownloadRecord
    )
    
    @admin.register(KnowledgeBase)
    class KnowledgeBaseAdmin(admin.ModelAdmin):
        """知识库 Admin 配置"""
        
        list_display = [
            'name', 
            'uploader', 
            'is_public', 
            'is_pending', 
            'star_count', 
            'downloads', 
            'create_datetime'
        ]
        list_filter = ['is_public', 'is_pending', 'create_datetime']
        search_fields = ['name', 'description', 'tags']
        raw_id_fields = ['uploader']
        date_hierarchy = 'create_datetime'
        readonly_fields = ['create_datetime', 'update_datetime']
        
        fieldsets = (
            ('基本信息', {
                'fields': ('name', 'description', 'uploader', 'copyright_owner')
            }),
            ('内容信息', {
                'fields': ('content', 'tags', 'base_path', 'version')
            }),
            ('状态信息', {
                'fields': ('is_public', 'is_pending', 'rejection_reason')
            }),
            ('统计信息', {
                'fields': ('star_count', 'downloads')
            }),
            ('时间信息', {
                'fields': ('create_datetime', 'update_datetime'),
                'classes': ('collapse',)
            }),
        )


    @admin.register(PersonaCard)
    class PersonaCardAdmin(admin.ModelAdmin):
        """人设卡 Admin 配置"""
        
        list_display = [
            'name', 
            'uploader', 
            'is_public', 
            'is_pending', 
            'star_count', 
            'downloads', 
            'create_datetime'
        ]
        list_filter = ['is_public', 'is_pending', 'create_datetime']
        search_fields = ['name', 'description', 'tags']
        raw_id_fields = ['uploader']
        date_hierarchy = 'create_datetime'
        readonly_fields = ['create_datetime', 'update_datetime']
        
        fieldsets = (
            ('基本信息', {
                'fields': ('name', 'description', 'uploader', 'copyright_owner')
            }),
            ('内容信息', {
                'fields': ('content', 'tags', 'base_path', 'version')
            }),
            ('状态信息', {
                'fields': ('is_public', 'is_pending', 'rejection_reason')
            }),
            ('统计信息', {
                'fields': ('star_count', 'downloads')
            }),
            ('时间信息', {
                'fields': ('create_datetime', 'update_datetime'),
                'classes': ('collapse',)
            }),
        )


    @admin.register(KnowledgeBaseFile)
    class KnowledgeBaseFileAdmin(admin.ModelAdmin):
        """知识库文件 Admin 配置"""
        
        list_display = [
            'file_name',
            'original_name',
            'file_type',
            'file_size',
            'create_datetime'
        ]
        list_filter = ['file_type', 'create_datetime']
        search_fields = ['file_name', 'original_name']
        raw_id_fields = ['knowledge_base']
        date_hierarchy = 'create_datetime'
        readonly_fields = ['create_datetime', 'update_datetime']
        
        fieldsets = (
            ('文件信息', {
                'fields': ('knowledge_base', 'file_name', 'original_name', 'file_path')
            }),
            ('文件属性', {
                'fields': ('file_type', 'file_size')
            }),
            ('时间信息', {
                'fields': ('create_datetime', 'update_datetime'),
                'classes': ('collapse',)
            }),
        )


    @admin.register(PersonaCardFile)
    class PersonaCardFileAdmin(admin.ModelAdmin):
        """人设卡文件 Admin 配置"""
        
        list_display = [
            'file_name',
            'original_name',
            'file_type',
            'file_size',
            'create_datetime'
        ]
        list_filter = ['file_type', 'create_datetime']
        search_fields = ['file_name', 'original_name']
        raw_id_fields = ['persona_card']
        date_hierarchy = 'create_datetime'
        readonly_fields = ['create_datetime', 'update_datetime']
        
        fieldsets = (
            ('文件信息', {
                'fields': ('persona_card', 'file_name', 'original_name', 'file_path')
            }),
            ('文件属性', {
                'fields': ('file_type', 'file_size')
            }),
            ('时间信息', {
                'fields': ('create_datetime', 'update_datetime'),
                'classes': ('collapse',)
            }),
        )


    @admin.register(Comment)
    class CommentAdmin(admin.ModelAdmin):
        """评论 Admin 配置"""
        
        list_display = [
            'user',
            'target_type',
            'content_preview',
            'is_deleted',
            'like_count',
            'create_datetime'
        ]
        list_filter = ['target_type', 'is_deleted', 'create_datetime']
        search_fields = ['content', 'user__username']
        raw_id_fields = ['user', 'parent']
        date_hierarchy = 'create_datetime'
        readonly_fields = ['create_datetime', 'update_datetime']
        
        fieldsets = (
            ('评论信息', {
                'fields': ('user', 'target_id', 'target_type', 'parent', 'content')
            }),
            ('状态信息', {
                'fields': ('is_deleted', 'like_count', 'dislike_count')
            }),
            ('时间信息', {
                'fields': ('create_datetime', 'update_datetime'),
                'classes': ('collapse',)
            }),
        )
        
        def content_preview(self, obj):
            """显示评论内容前 50 个字符"""
            return obj.content[:50] if obj.content else ''
        content_preview.short_description = '评论内容'


    @admin.register(CommentReaction)
    class CommentReactionAdmin(admin.ModelAdmin):
        """评论反应 Admin 配置"""
        
        list_display = [
            'user',
            'comment',
            'reaction_type',
            'create_datetime'
        ]
        list_filter = ['reaction_type', 'create_datetime']
        search_fields = ['user__username', 'comment__content']
        raw_id_fields = ['user', 'comment']
        date_hierarchy = 'create_datetime'
        readonly_fields = ['create_datetime', 'update_datetime']
        
        fieldsets = (
            ('反应信息', {
                'fields': ('user', 'comment', 'reaction_type')
            }),
            ('时间信息', {
                'fields': ('create_datetime', 'update_datetime'),
                'classes': ('collapse',)
            }),
        )


    @admin.register(StarRecord)
    class StarRecordAdmin(admin.ModelAdmin):
        """收藏记录 Admin 配置"""
        
        list_display = [
            'user',
            'target_type',
            'target_id',
            'create_datetime'
        ]
        list_filter = ['target_type', 'create_datetime']
        search_fields = ['user__username', 'target_id']
        raw_id_fields = ['user']
        date_hierarchy = 'create_datetime'
        readonly_fields = ['create_datetime', 'update_datetime']
        
        fieldsets = (
            ('收藏信息', {
                'fields': ('user', 'target_id', 'target_type')
            }),
            ('时间信息', {
                'fields': ('create_datetime', 'update_datetime'),
                'classes': ('collapse',)
            }),
        )


    @admin.register(EmailVerification)
    class EmailVerificationAdmin(admin.ModelAdmin):
        """邮箱验证 Admin 配置"""
        
        list_display = [
            'email',
            'code',
            'is_used',
            'expires_at',
            'create_datetime'
        ]
        list_filter = ['is_used', 'expires_at', 'create_datetime']
        search_fields = ['email', 'code']
        date_hierarchy = 'create_datetime'
        readonly_fields = ['create_datetime', 'update_datetime']
        
        fieldsets = (
            ('验证信息', {
                'fields': ('email', 'code', 'is_used', 'expires_at')
            }),
            ('时间信息', {
                'fields': ('create_datetime', 'update_datetime'),
                'classes': ('collapse',)
            }),
        )


    @admin.register(UploadRecord)
    class UploadRecordAdmin(admin.ModelAdmin):
        """上传记录 Admin 配置"""
        
        list_display = [
            'name',
            'uploader',
            'target_type',
            'status',
            'create_datetime'
        ]
        list_filter = ['target_type', 'status', 'create_datetime']
        search_fields = ['name', 'description', 'uploader__username', 'target_id']
        raw_id_fields = ['uploader']
        date_hierarchy = 'create_datetime'
        readonly_fields = ['create_datetime', 'update_datetime']
        
        fieldsets = (
            ('基本信息', {
                'fields': ('name', 'description', 'uploader')
            }),
            ('目标信息', {
                'fields': ('target_id', 'target_type')
            }),
            ('审核信息', {
                'fields': ('status',)
            }),
            ('时间信息', {
                'fields': ('create_datetime', 'update_datetime'),
                'classes': ('collapse',)
            }),
        )


    @admin.register(DownloadRecord)
    class DownloadRecordAdmin(admin.ModelAdmin):
        """下载记录 Admin 配置"""
        
        list_display = [
            'target_id',
            'target_type',
            'create_datetime'
        ]
        list_filter = ['target_type', 'create_datetime']
        search_fields = ['target_id']
        date_hierarchy = 'create_datetime'
        readonly_fields = ['create_datetime', 'update_datetime']
        
        fieldsets = (
            ('下载信息', {
                'fields': ('target_id', 'target_type')
            }),
            ('时间信息', {
                'fields': ('create_datetime', 'update_datetime'),
                'classes': ('collapse',)
            }),
        )

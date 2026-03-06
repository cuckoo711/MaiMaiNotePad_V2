from django.contrib import admin
from mainotebook.system.models import Translation


@admin.register(Translation)
class TranslationAdmin(admin.ModelAdmin):
    """翻译模型管理"""
    
    list_display = [
        'source_text',
        'translated_text',
        'translation_type',
        'source_language',
        'target_language',
        'sort',
        'status'
    ]
    
    list_filter = [
        'translation_type',
        'source_language',
        'status'
    ]
    
    search_fields = [
        'source_text',
        'translated_text'
    ]
    
    ordering = ['sort']

"""
属性测试模块

使用 Hypothesis 进行基于属性的测试，验证模型的通用属性。
"""

import uuid
import re
from datetime import datetime, timedelta
from django.test import TestCase
from django.db import models
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import from_model, TestCase as HypothesisTestCase

from mainotebook.system.models import Users
from mainotebook.content.models import (
    KnowledgeBase, KnowledgeBaseFile,
    PersonaCard, PersonaCardFile,
    Comment, CommentReaction,
    StarRecord, EmailVerification,
    UploadRecord, DownloadRecord
)


# 配置 Hypothesis
settings.register_profile("default", max_examples=50, deadline=None)
settings.load_profile("default")


class FieldTypeMappingPropertyTest(TestCase):
    """字段类型映射属性测试
    
    **Validates: Requirements 11.1-11.7**
    
    验证所有模型字段类型符合 SQLAlchemy 到 Django 的映射规则：
    - String → CharField/UUIDField
    - Text → TextField
    - Integer → IntegerField
    - Boolean → BooleanField
    - DateTime → DateTimeField
    - relationship → ForeignKey/OneToOneField
    """
    
    def setUp(self):
        """测试前准备"""
        self.user = Users.objects.create(
            username='testuser',
            email='test@example.com',
            name='测试用户'
        )
    
    def test_knowledge_base_field_types(self):
        """测试知识库字段类型正确性
        
        **Validates: Requirements 11.1-11.7**
        """
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='描述',
            uploader=self.user,
            version='1.0'
        )
        
        # 验证 UUID 字段
        self.assertIsInstance(kb.id, uuid.UUID)
        self.assertIsInstance(kb._meta.get_field('id'), models.UUIDField)
        
        # 验证 CharField 字段
        self.assertIsInstance(kb.name, str)
        self.assertIsInstance(kb._meta.get_field('name'), models.CharField)
        self.assertEqual(kb._meta.get_field('name').max_length, 200)
        
        self.assertIsInstance(kb._meta.get_field('version'), models.CharField)
        self.assertEqual(kb._meta.get_field('version').max_length, 50)
        
        # 验证 TextField 字段
        self.assertIsInstance(kb.description, str)
        self.assertIsInstance(kb._meta.get_field('description'), models.TextField)
        self.assertIsInstance(kb._meta.get_field('content'), models.TextField)
        self.assertIsInstance(kb._meta.get_field('tags'), models.TextField)
        self.assertIsInstance(kb._meta.get_field('base_path'), models.TextField)
        
        # 验证 IntegerField 字段
        self.assertIsInstance(kb.star_count, int)
        self.assertIsInstance(kb._meta.get_field('star_count'), models.IntegerField)
        self.assertIsInstance(kb.downloads, int)
        self.assertIsInstance(kb._meta.get_field('downloads'), models.IntegerField)
        
        # 验证 BooleanField 字段
        self.assertIsInstance(kb.is_public, bool)
        self.assertIsInstance(kb._meta.get_field('is_public'), models.BooleanField)
        self.assertIsInstance(kb.is_pending, bool)
        self.assertIsInstance(kb._meta.get_field('is_pending'), models.BooleanField)
        
        # 验证 ForeignKey 字段
        self.assertIsInstance(kb._meta.get_field('uploader'), models.ForeignKey)
        self.assertEqual(kb.uploader, self.user)
        
        # 验证 DateTimeField 字段（继承自 CoreModel）
        self.assertIsInstance(kb.create_datetime, datetime)
        self.assertIsInstance(kb._meta.get_field('create_datetime'), models.DateTimeField)
        self.assertIsInstance(kb.update_datetime, datetime)
        self.assertIsInstance(kb._meta.get_field('update_datetime'), models.DateTimeField)
        
        # 验证默认值
        self.assertEqual(kb.star_count, 0)
        self.assertEqual(kb.downloads, 0)
        self.assertEqual(kb.base_path, "[]")
        self.assertFalse(kb.is_public)
        self.assertTrue(kb.is_pending)
        self.assertEqual(kb.version, '1.0')
    
    def test_persona_card_field_types(self):
        """测试人设卡字段类型正确性
        
        **Validates: Requirements 11.1-11.7**
        """
        pc = PersonaCard.objects.create(
            name='测试人设卡',
            description='描述',
            uploader=self.user,
            version='2.0'
        )
        
        # 验证 UUID 字段
        self.assertIsInstance(pc.id, uuid.UUID)
        self.assertIsInstance(pc._meta.get_field('id'), models.UUIDField)
        
        # 验证 CharField 字段
        self.assertIsInstance(pc.name, str)
        self.assertIsInstance(pc._meta.get_field('name'), models.CharField)
        
        # 验证 TextField 字段
        self.assertIsInstance(pc.description, str)
        self.assertIsInstance(pc._meta.get_field('description'), models.TextField)
        
        # 验证 IntegerField 字段
        self.assertIsInstance(pc.star_count, int)
        self.assertIsInstance(pc._meta.get_field('star_count'), models.IntegerField)
        
        # 验证 BooleanField 字段
        self.assertIsInstance(pc.is_public, bool)
        self.assertIsInstance(pc._meta.get_field('is_public'), models.BooleanField)
        
        # 验证 ForeignKey 字段
        self.assertIsInstance(pc._meta.get_field('uploader'), models.ForeignKey)
        
        # 验证默认值
        self.assertEqual(pc.star_count, 0)
        self.assertEqual(pc.downloads, 0)
        self.assertFalse(pc.is_public)
        self.assertTrue(pc.is_pending)
    
    def test_knowledge_base_file_field_types(self):
        """测试知识库文件字段类型正确性
        
        **Validates: Requirements 11.1-11.7**
        """
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='描述',
            uploader=self.user
        )
        
        kb_file = KnowledgeBaseFile.objects.create(
            knowledge_base=kb,
            file_name='test.pdf',
            original_name='测试文件.pdf',
            file_path='/path/to/file',
            file_type='application/pdf',
            file_size=1024
        )
        
        # 验证 UUID 字段
        self.assertIsInstance(kb_file.id, uuid.UUID)
        self.assertIsInstance(kb_file._meta.get_field('id'), models.UUIDField)
        
        # 验证 CharField 字段
        self.assertIsInstance(kb_file.file_name, str)
        self.assertIsInstance(kb_file._meta.get_field('file_name'), models.CharField)
        self.assertEqual(kb_file._meta.get_field('file_name').max_length, 255)
        
        # 验证 BigIntegerField 字段
        self.assertIsInstance(kb_file.file_size, int)
        self.assertIsInstance(kb_file._meta.get_field('file_size'), models.BigIntegerField)
        
        # 验证 ForeignKey 字段
        self.assertIsInstance(kb_file._meta.get_field('knowledge_base'), models.ForeignKey)
        self.assertEqual(kb_file.knowledge_base, kb)
        
        # 验证默认值
        self.assertEqual(kb_file.file_size, 1024)
    
    def test_comment_field_types(self):
        """测试评论字段类型正确性
        
        **Validates: Requirements 11.1-11.7**
        """
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='描述',
            uploader=self.user
        )
        
        comment = Comment.objects.create(
            user=self.user,
            target_id=str(kb.id),
            target_type='knowledge',
            content='测试评论'
        )
        
        # 验证 UUID 字段
        self.assertIsInstance(comment.id, uuid.UUID)
        self.assertIsInstance(comment._meta.get_field('id'), models.UUIDField)
        
        # 验证 CharField 字段
        self.assertIsInstance(comment.target_id, str)
        self.assertIsInstance(comment._meta.get_field('target_id'), models.CharField)
        self.assertEqual(comment._meta.get_field('target_id').max_length, 36)
        
        self.assertIsInstance(comment.target_type, str)
        self.assertIsInstance(comment._meta.get_field('target_type'), models.CharField)
        
        # 验证 TextField 字段
        self.assertIsInstance(comment.content, str)
        self.assertIsInstance(comment._meta.get_field('content'), models.TextField)
        
        # 验证 BooleanField 字段
        self.assertIsInstance(comment.is_deleted, bool)
        self.assertIsInstance(comment._meta.get_field('is_deleted'), models.BooleanField)
        
        # 验证 IntegerField 字段
        self.assertIsInstance(comment.like_count, int)
        self.assertIsInstance(comment._meta.get_field('like_count'), models.IntegerField)
        
        # 验证 ForeignKey 字段
        self.assertIsInstance(comment._meta.get_field('user'), models.ForeignKey)
        self.assertIsInstance(comment._meta.get_field('parent'), models.ForeignKey)
        
        # 验证默认值
        self.assertFalse(comment.is_deleted)
        self.assertEqual(comment.like_count, 0)
        self.assertEqual(comment.dislike_count, 0)
    
    def test_star_record_field_types(self):
        """测试收藏记录字段类型正确性
        
        **Validates: Requirements 11.1-11.7**
        """
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='描述',
            uploader=self.user
        )
        
        star = StarRecord.objects.create(
            user=self.user,
            target_id=str(kb.id),
            target_type='knowledge'
        )
        
        # 验证 UUID 字段
        self.assertIsInstance(star.id, uuid.UUID)
        self.assertIsInstance(star._meta.get_field('id'), models.UUIDField)
        
        # 验证 CharField 字段
        self.assertIsInstance(star.target_id, str)
        self.assertIsInstance(star._meta.get_field('target_id'), models.CharField)
        self.assertIsInstance(star.target_type, str)
        self.assertIsInstance(star._meta.get_field('target_type'), models.CharField)
        
        # 验证 ForeignKey 字段
        self.assertIsInstance(star._meta.get_field('user'), models.ForeignKey)
    
    def test_email_verification_field_types(self):
        """测试邮箱验证字段类型正确性
        
        **Validates: Requirements 11.1-11.7**
        """
        expires_at = datetime.now() + timedelta(minutes=10)
        verification = EmailVerification.objects.create(
            email='test@example.com',
            code='123456',
            expires_at=expires_at
        )
        
        # 验证 UUID 字段
        self.assertIsInstance(verification.id, uuid.UUID)
        self.assertIsInstance(verification._meta.get_field('id'), models.UUIDField)
        
        # 验证 EmailField 字段
        self.assertIsInstance(verification.email, str)
        self.assertIsInstance(verification._meta.get_field('email'), models.EmailField)
        
        # 验证 CharField 字段
        self.assertIsInstance(verification.code, str)
        self.assertIsInstance(verification._meta.get_field('code'), models.CharField)
        
        # 验证 BooleanField 字段
        self.assertIsInstance(verification.is_used, bool)
        self.assertIsInstance(verification._meta.get_field('is_used'), models.BooleanField)
        
        # 验证 DateTimeField 字段
        self.assertIsInstance(verification.expires_at, datetime)
        self.assertIsInstance(verification._meta.get_field('expires_at'), models.DateTimeField)
        
        # 验证默认值
        self.assertFalse(verification.is_used)
    
    def test_upload_record_field_types(self):
        """测试上传记录字段类型正确性
        
        **Validates: Requirements 11.1-11.7**
        """
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='描述',
            uploader=self.user
        )
        
        upload = UploadRecord.objects.create(
            uploader=self.user,
            target_id=str(kb.id),
            target_type='knowledge',
            name='测试上传'
        )
        
        # 验证 UUID 字段
        self.assertIsInstance(upload.id, uuid.UUID)
        self.assertIsInstance(upload._meta.get_field('id'), models.UUIDField)
        
        # 验证 CharField 字段
        self.assertIsInstance(upload.target_id, str)
        self.assertIsInstance(upload._meta.get_field('target_id'), models.CharField)
        self.assertIsInstance(upload.name, str)
        self.assertIsInstance(upload._meta.get_field('name'), models.CharField)
        self.assertIsInstance(upload.status, str)
        self.assertIsInstance(upload._meta.get_field('status'), models.CharField)
        
        # 验证 TextField 字段
        self.assertIsInstance(upload._meta.get_field('description'), models.TextField)
        
        # 验证 ForeignKey 字段
        self.assertIsInstance(upload._meta.get_field('uploader'), models.ForeignKey)
        
        # 验证默认值
        self.assertEqual(upload.status, 'pending')
    
    def test_download_record_field_types(self):
        """测试下载记录字段类型正确性
        
        **Validates: Requirements 11.1-11.7**
        """
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='描述',
            uploader=self.user
        )
        
        download = DownloadRecord.objects.create(
            target_id=str(kb.id),
            target_type='knowledge'
        )
        
        # 验证 UUID 字段
        self.assertIsInstance(download.id, uuid.UUID)
        self.assertIsInstance(download._meta.get_field('id'), models.UUIDField)
        
        # 验证 CharField 字段
        self.assertIsInstance(download.target_id, str)
        self.assertIsInstance(download._meta.get_field('target_id'), models.CharField)
        self.assertIsInstance(download.target_type, str)
        self.assertIsInstance(download._meta.get_field('target_type'), models.CharField)



class ForeignKeyRelationshipPropertyTest(TestCase):
    """外键关系配置属性测试
    
    **Validates: Requirements 12.1-12.3**
    
    验证所有外键字段都正确配置了：
    - on_delete 参数
    - related_name 参数
    - 多个外键指向同一模型时，related_name 不冲突
    """
    
    def test_all_foreign_keys_have_on_delete(self):
        """测试所有外键都设置了 on_delete
        
        **Validates: Requirements 12.1**
        """
        from mainotebook.content import models as content_models
        
        # 获取所有模型类
        model_classes = [
            KnowledgeBase, KnowledgeBaseFile,
            PersonaCard, PersonaCardFile,
            Comment, CommentReaction,
            StarRecord, UploadRecord, DownloadRecord
        ]
        
        for model_class in model_classes:
            for field in model_class._meta.get_fields():
                if isinstance(field, (models.ForeignKey, models.OneToOneField)):
                    # 验证 on_delete 已设置
                    self.assertIsNotNone(
                        field.remote_field.on_delete,
                        f"{model_class.__name__}.{field.name} 缺少 on_delete 参数"
                    )
    
    def test_all_foreign_keys_have_related_name(self):
        """测试所有外键都设置了 related_name
        
        **Validates: Requirements 12.2**
        """
        model_classes = [
            KnowledgeBase, KnowledgeBaseFile,
            PersonaCard, PersonaCardFile,
            Comment, CommentReaction,
            StarRecord, UploadRecord, DownloadRecord
        ]
        
        # 从 CoreModel 继承的字段，可以没有 related_name
        inherited_fields = ['creator', 'modifier']
        
        for model_class in model_classes:
            for field in model_class._meta.get_fields():
                if isinstance(field, (models.ForeignKey, models.OneToOneField)):
                    # 跳过从 CoreModel 继承的字段
                    if field.name in inherited_fields:
                        continue
                    
                    # 验证 related_name 已设置
                    self.assertIsNotNone(
                        field.remote_field.related_name,
                        f"{model_class.__name__}.{field.name} 缺少 related_name 参数"
                    )
    
    def test_related_names_are_unique(self):
        """测试同一模型的多个外键有不同的 related_name
        
        **Validates: Requirements 12.3**
        """
        model_classes = [
            KnowledgeBase, KnowledgeBaseFile,
            PersonaCard, PersonaCardFile,
            Comment, CommentReaction,
            StarRecord, UploadRecord, DownloadRecord
        ]
        
        for model_class in model_classes:
            # 收集指向同一模型的外键
            foreign_keys_by_target = {}
            
            for field in model_class._meta.get_fields():
                if isinstance(field, (models.ForeignKey, models.OneToOneField)):
                    target_model = field.remote_field.model
                    if target_model not in foreign_keys_by_target:
                        foreign_keys_by_target[target_model] = []
                    foreign_keys_by_target[target_model].append(field)
            
            # 验证指向同一模型的外键有不同的 related_name
            for target_model, fields in foreign_keys_by_target.items():
                if len(fields) > 1:
                    related_names = [f.remote_field.related_name for f in fields]
                    self.assertEqual(
                        len(related_names),
                        len(set(related_names)),
                        f"{model_class.__name__} 中指向 {target_model.__name__} 的外键有重复的 related_name: {related_names}"
                    )
    
    def test_foreign_key_on_delete_values(self):
        """测试外键的 on_delete 值符合设计要求
        
        **Validates: Requirements 12.1**
        """
        # 验证 KnowledgeBase.uploader 使用 PROTECT
        kb_uploader_field = KnowledgeBase._meta.get_field('uploader')
        self.assertEqual(kb_uploader_field.remote_field.on_delete, models.PROTECT)
        
        # 验证 KnowledgeBaseFile.knowledge_base 使用 CASCADE
        kbf_kb_field = KnowledgeBaseFile._meta.get_field('knowledge_base')
        self.assertEqual(kbf_kb_field.remote_field.on_delete, models.CASCADE)
        
        # 验证 PersonaCard.uploader 使用 PROTECT
        pc_uploader_field = PersonaCard._meta.get_field('uploader')
        self.assertEqual(pc_uploader_field.remote_field.on_delete, models.PROTECT)
        
        # 验证 PersonaCardFile.persona_card 使用 CASCADE
        pcf_pc_field = PersonaCardFile._meta.get_field('persona_card')
        self.assertEqual(pcf_pc_field.remote_field.on_delete, models.CASCADE)
        
        # 验证 Comment.user 使用 PROTECT
        comment_user_field = Comment._meta.get_field('user')
        self.assertEqual(comment_user_field.remote_field.on_delete, models.PROTECT)
        
        # 验证 Comment.parent 使用 CASCADE
        comment_parent_field = Comment._meta.get_field('parent')
        self.assertEqual(comment_parent_field.remote_field.on_delete, models.CASCADE)
        
        # 验证 CommentReaction.comment 使用 CASCADE
        cr_comment_field = CommentReaction._meta.get_field('comment')
        self.assertEqual(cr_comment_field.remote_field.on_delete, models.CASCADE)
        
        # 验证 StarRecord.user 使用 CASCADE
        star_user_field = StarRecord._meta.get_field('user')
        self.assertEqual(star_user_field.remote_field.on_delete, models.CASCADE)
        
        # 验证 UploadRecord.uploader 使用 PROTECT
        upload_uploader_field = UploadRecord._meta.get_field('uploader')
        self.assertEqual(upload_uploader_field.remote_field.on_delete, models.PROTECT)


class ModelMetadataPropertyTest(TestCase):
    """模型元数据属性测试
    
    **Validates: Requirements 13.1-13.3**
    
    验证所有模型都包含：
    - Meta 类（db_table, verbose_name, ordering）
    - __str__ 方法
    - 中文 docstring
    """
    
    def test_all_models_have_meta_class(self):
        """测试所有模型都有 Meta 类
        
        **Validates: Requirements 13.1**
        """
        model_classes = [
            KnowledgeBase, KnowledgeBaseFile,
            PersonaCard, PersonaCardFile,
            Comment, CommentReaction,
            StarRecord, EmailVerification,
            UploadRecord, DownloadRecord
        ]
        
        for model_class in model_classes:
            # 验证 Meta 类存在
            self.assertTrue(
                hasattr(model_class, '_meta'),
                f"{model_class.__name__} 缺少 Meta 类"
            )
            
            # 验证 db_table 已设置
            self.assertIsNotNone(
                model_class._meta.db_table,
                f"{model_class.__name__} 缺少 db_table"
            )
            
            # 验证 verbose_name 已设置
            self.assertIsNotNone(
                model_class._meta.verbose_name,
                f"{model_class.__name__} 缺少 verbose_name"
            )
            
            # 验证 ordering 已设置
            self.assertIsNotNone(
                model_class._meta.ordering,
                f"{model_class.__name__} 缺少 ordering"
            )
    
    def test_all_models_have_str_method(self):
        """测试所有模型都有 __str__ 方法
        
        **Validates: Requirements 13.2**
        """
        model_classes = [
            KnowledgeBase, KnowledgeBaseFile,
            PersonaCard, PersonaCardFile,
            Comment, CommentReaction,
            StarRecord, EmailVerification,
            UploadRecord, DownloadRecord
        ]
        
        for model_class in model_classes:
            # 验证 __str__ 方法存在
            self.assertTrue(
                hasattr(model_class, '__str__'),
                f"{model_class.__name__} 缺少 __str__ 方法"
            )
            
            # 验证 __str__ 方法不是继承自 Model 的默认实现
            self.assertNotEqual(
                model_class.__str__,
                models.Model.__str__,
                f"{model_class.__name__} 的 __str__ 方法未重写"
            )
    
    def test_all_models_have_chinese_docstring(self):
        """测试所有模型都有中文 docstring
        
        **Validates: Requirements 13.4**
        """
        model_classes = [
            KnowledgeBase, KnowledgeBaseFile,
            PersonaCard, PersonaCardFile,
            Comment, CommentReaction,
            StarRecord, EmailVerification,
            UploadRecord, DownloadRecord
        ]
        
        for model_class in model_classes:
            # 验证 docstring 存在
            self.assertIsNotNone(
                model_class.__doc__,
                f"{model_class.__name__} 缺少 docstring"
            )
            
            # 验证 docstring 包含中文字符
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in model_class.__doc__)
            self.assertTrue(
                has_chinese,
                f"{model_class.__name__} 的 docstring 不包含中文"
            )
    
    def test_db_table_naming_convention(self):
        """测试数据库表名遵循命名规范
        
        **Validates: Requirements 13.1**
        """
        model_classes = [
            KnowledgeBase, KnowledgeBaseFile,
            PersonaCard, PersonaCardFile,
            Comment, CommentReaction,
            StarRecord, EmailVerification,
            UploadRecord, DownloadRecord
        ]
        
        for model_class in model_classes:
            db_table = model_class._meta.db_table
            # 验证表名以 table_prefix 开头（mainotebook_）
            self.assertTrue(
                db_table.startswith('mainotebook_'),
                f"{model_class.__name__} 的 db_table '{db_table}' 不符合命名规范"
            )
            
            # 验证表名包含 'content'
            self.assertIn(
                'content',
                db_table,
                f"{model_class.__name__} 的 db_table '{db_table}' 不包含 'content'"
            )
    
    def test_verbose_name_is_chinese(self):
        """测试 verbose_name 使用中文
        
        **Validates: Requirements 13.1**
        """
        model_classes = [
            KnowledgeBase, KnowledgeBaseFile,
            PersonaCard, PersonaCardFile,
            Comment, CommentReaction,
            StarRecord, EmailVerification,
            UploadRecord, DownloadRecord
        ]
        
        for model_class in model_classes:
            verbose_name = str(model_class._meta.verbose_name)
            # 验证 verbose_name 包含中文字符
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in verbose_name)
            self.assertTrue(
                has_chinese,
                f"{model_class.__name__} 的 verbose_name '{verbose_name}' 不是中文"
            )


class CodeStylePropertyTest(TestCase):
    """代码规范属性测试
    
    **Validates: Requirements 15.1-15.5**
    
    验证代码遵循规范：
    - 模型类名使用 PascalCase
    - 字段名使用 snake_case
    - docstring 包含中文
    """
    
    def test_model_naming_convention(self):
        """测试模型命名规范
        
        **Validates: Requirements 15.1, 15.5**
        """
        model_classes = [
            KnowledgeBase, KnowledgeBaseFile,
            PersonaCard, PersonaCardFile,
            Comment, CommentReaction,
            StarRecord, EmailVerification,
            UploadRecord, DownloadRecord
        ]
        
        for model_class in model_classes:
            # 验证类名使用 PascalCase
            self.assertTrue(
                re.match(r'^[A-Z][a-zA-Z0-9]*$', model_class.__name__),
                f"{model_class.__name__} 不符合 PascalCase 命名规范"
            )
    
    def test_field_naming_convention(self):
        """测试字段命名规范
        
        **Validates: Requirements 15.1, 15.5**
        """
        model_classes = [
            KnowledgeBase, KnowledgeBaseFile,
            PersonaCard, PersonaCardFile,
            Comment, CommentReaction,
            StarRecord, EmailVerification,
            UploadRecord, DownloadRecord
        ]
        
        for model_class in model_classes:
            # 验证字段名使用 snake_case
            for field in model_class._meta.get_fields():
                if hasattr(field, 'name') and not field.name.startswith('_'):
                    self.assertTrue(
                        re.match(r'^[a-z][a-z0-9_]*$', field.name),
                        f"{model_class.__name__}.{field.name} 不符合 snake_case 命名规范"
                    )
    
    def test_method_docstrings_are_chinese(self):
        """测试方法 docstring 使用中文
        
        **Validates: Requirements 15.2**
        """
        # 测试 to_dict 方法的 docstring
        kb_to_dict_doc = KnowledgeBase.to_dict.__doc__
        self.assertIsNotNone(kb_to_dict_doc)
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in kb_to_dict_doc)
        self.assertTrue(has_chinese, "KnowledgeBase.to_dict 的 docstring 不包含中文")
        
        pc_to_dict_doc = PersonaCard.to_dict.__doc__
        self.assertIsNotNone(pc_to_dict_doc)
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in pc_to_dict_doc)
        self.assertTrue(has_chinese, "PersonaCard.to_dict 的 docstring 不包含中文")
    
    def test_field_verbose_names_are_chinese(self):
        """测试字段 verbose_name 使用中文
        
        **Validates: Requirements 15.2**
        """
        model_classes = [
            KnowledgeBase, KnowledgeBaseFile,
            PersonaCard, PersonaCardFile,
            Comment, CommentReaction,
            StarRecord, EmailVerification,
            UploadRecord, DownloadRecord
        ]
        
        for model_class in model_classes:
            for field in model_class._meta.get_fields():
                if hasattr(field, 'verbose_name') and field.verbose_name:
                    verbose_name = str(field.verbose_name)
                    # 跳过自动生成的 verbose_name（如 'ID'）
                    if verbose_name.lower() in ['id', 'ID']:
                        continue
                    
                    # 验证 verbose_name 包含中文字符
                    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in verbose_name)
                    self.assertTrue(
                        has_chinese,
                        f"{model_class.__name__}.{field.name} 的 verbose_name '{verbose_name}' 不是中文"
                    )
    
    def test_choices_display_names_are_chinese(self):
        """测试 choices 的显示名称使用中文
        
        **Validates: Requirements 15.2**
        """
        # 测试 Comment.target_type 的 choices
        target_type_field = Comment._meta.get_field('target_type')
        for value, display in target_type_field.choices:
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in display)
            self.assertTrue(
                has_chinese,
                f"Comment.target_type 的 choice '{value}' 的显示名称 '{display}' 不是中文"
            )
        
        # 测试 CommentReaction.reaction_type 的 choices
        reaction_type_field = CommentReaction._meta.get_field('reaction_type')
        for value, display in reaction_type_field.choices:
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in display)
            self.assertTrue(
                has_chinese,
                f"CommentReaction.reaction_type 的 choice '{value}' 的显示名称 '{display}' 不是中文"
            )
        
        # 测试 UploadRecord.status 的 choices
        status_field = UploadRecord._meta.get_field('status')
        for value, display in status_field.choices:
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in display)
            self.assertTrue(
                has_chinese,
                f"UploadRecord.status 的 choice '{value}' 的显示名称 '{display}' 不是中文"
            )

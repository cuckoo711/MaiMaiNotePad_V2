"""
Content 应用模型单元测试

测试所有内容模型的创建、字段验证、关系和方法。
"""

import uuid
from datetime import datetime, timedelta
from django.test import TestCase
from django.db import IntegrityError
from django.utils import timezone
from mainotebook.system.models import Users
from mainotebook.content.models import (
    KnowledgeBase, KnowledgeBaseFile,
    PersonaCard, PersonaCardFile,
    Comment, CommentReaction,
    StarRecord, EmailVerification,
    UploadRecord, DownloadRecord
)


class KnowledgeBaseModelTest(TestCase):
    """知识库模型单元测试
    
    验证需求：3.1, 3.2, 3.5
    """
    
    def setUp(self):
        """测试前准备"""
        self.user = Users.objects.create(
            username='testuser',
            email='test@example.com',
            name='测试用户'
        )
    
    def test_create_knowledge_base(self):
        """测试创建知识库"""
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='这是一个测试知识库',
            uploader=self.user,
            version='1.0'
        )
        
        # 验证基本字段
        self.assertEqual(kb.name, '测试知识库')
        self.assertEqual(kb.description, '这是一个测试知识库')
        self.assertEqual(kb.uploader, self.user)
        self.assertEqual(kb.version, '1.0')
        
        # 验证默认值
        self.assertEqual(kb.star_count, 0)
        self.assertEqual(kb.downloads, 0)
        self.assertFalse(kb.is_public)
        self.assertTrue(kb.is_pending)
        self.assertEqual(kb.base_path, "[]")
        
        # 验证 UUID 主键
        self.assertIsInstance(kb.id, uuid.UUID)
    
    def test_knowledge_base_to_dict(self):
        """测试 to_dict 方法"""
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='描述',
            uploader=self.user,
            content='测试内容',
            tags='标签1,标签2'
        )
        
        data = kb.to_dict()
        
        # 验证字典包含所有必要字段
        self.assertIn('id', data)
        self.assertIn('name', data)
        self.assertIn('description', data)
        self.assertIn('uploader_id', data)
        self.assertIn('content', data)
        self.assertIn('tags', data)
        self.assertIn('star_count', data)
        self.assertIn('downloads', data)
        self.assertIn('is_public', data)
        self.assertIn('is_pending', data)
        self.assertIn('version', data)
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)
        
        # 验证字段值
        self.assertEqual(data['name'], '测试知识库')
        self.assertEqual(data['content'], '测试内容')
        self.assertEqual(data['tags'], '标签1,标签2')
    
    def test_knowledge_base_str(self):
        """测试字符串表示"""
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='描述',
            uploader=self.user,
            version='2.0'
        )
        
        self.assertEqual(str(kb), '测试知识库 (v2.0)')
    
    def test_knowledge_base_foreign_key_relationship(self):
        """测试外键关系"""
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='描述',
            uploader=self.user
        )
        
        # 验证反向关系
        self.assertIn(kb, self.user.uploaded_knowledge_bases.all())
    
    def test_knowledge_base_optional_fields(self):
        """测试可选字段"""
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='描述',
            uploader=self.user,
            copyright_owner='版权所有者',
            rejection_reason='拒绝原因'
        )
        
        self.assertEqual(kb.copyright_owner, '版权所有者')
        self.assertEqual(kb.rejection_reason, '拒绝原因')


class KnowledgeBaseFileModelTest(TestCase):
    """知识库文件模型单元测试
    
    验证需求：3.2, 3.4
    """
    
    def setUp(self):
        """测试前准备"""
        self.user = Users.objects.create(
            username='testuser',
            email='test@example.com',
            name='测试用户'
        )
        self.kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='描述',
            uploader=self.user
        )
    
    def test_create_knowledge_base_file(self):
        """测试创建知识库文件"""
        kb_file = KnowledgeBaseFile.objects.create(
            knowledge_base=self.kb,
            file_name='test_file.pdf',
            original_name='测试文件.pdf',
            file_path='/path/to/file.pdf',
            file_type='application/pdf',
            file_size=1024000
        )
        
        # 验证字段
        self.assertEqual(kb_file.file_name, 'test_file.pdf')
        self.assertEqual(kb_file.original_name, '测试文件.pdf')
        self.assertEqual(kb_file.file_path, '/path/to/file.pdf')
        self.assertEqual(kb_file.file_type, 'application/pdf')
        self.assertEqual(kb_file.file_size, 1024000)
        
        # 验证外键关系
        self.assertEqual(kb_file.knowledge_base, self.kb)
    
    def test_knowledge_base_file_str(self):
        """测试字符串表示"""
        kb_file = KnowledgeBaseFile.objects.create(
            knowledge_base=self.kb,
            file_name='test.pdf',
            original_name='测试.pdf',
            file_path='/path/to/file',
            file_type='application/pdf'
        )
        
        self.assertEqual(str(kb_file), '测试.pdf (application/pdf)')
    
    def test_knowledge_base_file_relationship(self):
        """测试文件与知识库的关系"""
        file1 = KnowledgeBaseFile.objects.create(
            knowledge_base=self.kb,
            file_name='file1.pdf',
            original_name='文件1.pdf',
            file_path='/path/1',
            file_type='application/pdf'
        )
        file2 = KnowledgeBaseFile.objects.create(
            knowledge_base=self.kb,
            file_name='file2.txt',
            original_name='文件2.txt',
            file_path='/path/2',
            file_type='text/plain'
        )
        
        # 验证反向关系
        self.assertEqual(self.kb.files.count(), 2)
        self.assertIn(file1, self.kb.files.all())
        self.assertIn(file2, self.kb.files.all())
    
    def test_cascade_delete(self):
        """测试级联删除"""
        kb_file = KnowledgeBaseFile.objects.create(
            knowledge_base=self.kb,
            file_name='test.pdf',
            original_name='测试.pdf',
            file_path='/path/to/file',
            file_type='application/pdf'
        )
        
        file_id = kb_file.id
        
        # 删除知识库应该级联删除文件
        self.kb.delete()
        
        # 验证文件已被删除
        self.assertFalse(KnowledgeBaseFile.objects.filter(id=file_id).exists())


class PersonaCardModelTest(TestCase):
    """人设卡模型单元测试
    
    验证需求：4.1, 4.5
    """
    
    def setUp(self):
        """测试前准备"""
        self.user = Users.objects.create(
            username='testuser',
            email='test@example.com',
            name='测试用户'
        )
    
    def test_create_persona_card(self):
        """测试创建人设卡"""
        pc = PersonaCard.objects.create(
            name='测试人设卡',
            description='这是一个测试人设卡',
            uploader=self.user,
            version='1.0'
        )
        
        # 验证基本字段
        self.assertEqual(pc.name, '测试人设卡')
        self.assertEqual(pc.description, '这是一个测试人设卡')
        self.assertEqual(pc.uploader, self.user)
        self.assertEqual(pc.version, '1.0')
        
        # 验证默认值
        self.assertEqual(pc.star_count, 0)
        self.assertEqual(pc.downloads, 0)
        self.assertFalse(pc.is_public)
        self.assertTrue(pc.is_pending)
    
    def test_persona_card_to_dict(self):
        """测试 to_dict 方法"""
        pc = PersonaCard.objects.create(
            name='测试人设卡',
            description='描述',
            uploader=self.user,
            content='人设内容'
        )
        
        data = pc.to_dict()
        
        # 验证字典包含所有必要字段
        self.assertIn('id', data)
        self.assertIn('name', data)
        self.assertIn('uploader_id', data)
        self.assertEqual(data['name'], '测试人设卡')
        self.assertEqual(data['content'], '人设内容')
    
    def test_persona_card_str(self):
        """测试字符串表示"""
        pc = PersonaCard.objects.create(
            name='测试人设卡',
            description='描述',
            uploader=self.user,
            version='3.0'
        )
        
        self.assertEqual(str(pc), '测试人设卡 (v3.0)')
    
    def test_persona_card_foreign_key_relationship(self):
        """测试外键关系"""
        pc = PersonaCard.objects.create(
            name='测试人设卡',
            description='描述',
            uploader=self.user
        )
        
        # 验证反向关系
        self.assertIn(pc, self.user.uploaded_persona_cards.all())


class PersonaCardFileModelTest(TestCase):
    """人设卡文件模型单元测试
    
    验证需求：4.2, 4.4
    """
    
    def setUp(self):
        """测试前准备"""
        self.user = Users.objects.create(
            username='testuser',
            email='test@example.com',
            name='测试用户'
        )
        self.pc = PersonaCard.objects.create(
            name='测试人设卡',
            description='描述',
            uploader=self.user
        )
    
    def test_create_persona_card_file(self):
        """测试创建人设卡文件"""
        pc_file = PersonaCardFile.objects.create(
            persona_card=self.pc,
            file_name='persona.json',
            original_name='人设.json',
            file_path='/path/to/persona.json',
            file_type='application/json',
            file_size=2048
        )
        
        # 验证字段
        self.assertEqual(pc_file.file_name, 'persona.json')
        self.assertEqual(pc_file.original_name, '人设.json')
        self.assertEqual(pc_file.file_type, 'application/json')
        self.assertEqual(pc_file.file_size, 2048)
        
        # 验证外键关系
        self.assertEqual(pc_file.persona_card, self.pc)
    
    def test_persona_card_file_str(self):
        """测试字符串表示"""
        pc_file = PersonaCardFile.objects.create(
            persona_card=self.pc,
            file_name='test.json',
            original_name='测试.json',
            file_path='/path/to/file',
            file_type='application/json'
        )
        
        self.assertEqual(str(pc_file), '测试.json (application/json)')
    
    def test_persona_card_file_relationship(self):
        """测试文件与人设卡的关系"""
        file1 = PersonaCardFile.objects.create(
            persona_card=self.pc,
            file_name='file1.json',
            original_name='文件1.json',
            file_path='/path/1',
            file_type='application/json'
        )
        
        # 验证反向关系
        self.assertEqual(self.pc.files.count(), 1)
        self.assertIn(file1, self.pc.files.all())


class CommentModelTest(TestCase):
    """评论模型单元测试
    
    验证需求：9.1
    """
    
    def setUp(self):
        """测试前准备"""
        self.user = Users.objects.create(
            username='testuser',
            email='test@example.com',
            name='测试用户'
        )
        self.kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='描述',
            uploader=self.user
        )
    
    def test_create_comment(self):
        """测试创建评论"""
        comment = Comment.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            content='这是一条测试评论'
        )
        
        # 验证字段
        self.assertEqual(comment.user, self.user)
        self.assertEqual(comment.target_id, str(self.kb.id))
        self.assertEqual(comment.target_type, 'knowledge')
        self.assertEqual(comment.content, '这是一条测试评论')
        
        # 验证默认值
        self.assertFalse(comment.is_deleted)
        self.assertEqual(comment.like_count, 0)
        self.assertEqual(comment.dislike_count, 0)
        self.assertIsNone(comment.parent)
    
    def test_comment_str(self):
        """测试字符串表示"""
        comment = Comment.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            content='这是一条很长的评论内容，用于测试字符串表示方法是否正确截断内容'
        )
        
        str_repr = str(comment)
        self.assertIn('testuser', str_repr)
        self.assertIn('的评论:', str_repr)
        # 验证内容被截断到50个字符
        self.assertTrue(len(str_repr) < 100)
    
    def test_nested_comment(self):
        """测试嵌套评论"""
        parent_comment = Comment.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            content='父评论'
        )
        
        reply = Comment.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            content='回复评论',
            parent=parent_comment
        )
        
        # 验证父子关系
        self.assertEqual(reply.parent, parent_comment)
        self.assertIn(reply, parent_comment.replies.all())
        self.assertEqual(parent_comment.replies.count(), 1)
    
    def test_comment_soft_delete(self):
        """测试软删除功能"""
        comment = Comment.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            content='待删除的评论'
        )
        
        # 软删除
        comment.is_deleted = True
        comment.save()
        
        # 验证评论仍然存在但标记为已删除
        self.assertTrue(Comment.objects.filter(id=comment.id).exists())
        self.assertTrue(comment.is_deleted)
    
    def test_comment_target_type_choices(self):
        """测试目标类型选项"""
        # 测试知识库类型
        comment1 = Comment.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            content='知识库评论'
        )
        self.assertEqual(comment1.target_type, 'knowledge')
        
        # 测试人设卡类型
        comment2 = Comment.objects.create(
            user=self.user,
            target_id=str(uuid.uuid4()),
            target_type='persona',
            content='人设卡评论'
        )
        self.assertEqual(comment2.target_type, 'persona')


class CommentReactionModelTest(TestCase):
    """评论反应模型单元测试
    
    验证需求：9.2
    """
    
    def setUp(self):
        """测试前准备"""
        self.user = Users.objects.create(
            username='testuser',
            email='test@example.com',
            name='测试用户'
        )
        self.kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='描述',
            uploader=self.user
        )
        self.comment = Comment.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            content='测试评论'
        )
    
    def test_create_comment_reaction(self):
        """测试创建评论反应"""
        reaction = CommentReaction.objects.create(
            user=self.user,
            comment=self.comment,
            reaction_type='like'
        )
        
        # 验证字段
        self.assertEqual(reaction.user, self.user)
        self.assertEqual(reaction.comment, self.comment)
        self.assertEqual(reaction.reaction_type, 'like')
    
    def test_comment_reaction_str(self):
        """测试字符串表示"""
        reaction = CommentReaction.objects.create(
            user=self.user,
            comment=self.comment,
            reaction_type='like'
        )
        
        str_repr = str(reaction)
        self.assertIn('testuser', str_repr)
        self.assertIn('点赞', str_repr)
        self.assertIn('评论', str_repr)
    
    def test_comment_reaction_unique_constraint(self):
        """测试唯一约束"""
        # 创建第一个反应
        CommentReaction.objects.create(
            user=self.user,
            comment=self.comment,
            reaction_type='like'
        )
        
        # 尝试创建重复的反应应该失败
        with self.assertRaises(IntegrityError):
            CommentReaction.objects.create(
                user=self.user,
                comment=self.comment,
                reaction_type='dislike'
            )
    
    def test_comment_reaction_relationship(self):
        """测试反应与评论的关系"""
        reaction = CommentReaction.objects.create(
            user=self.user,
            comment=self.comment,
            reaction_type='like'
        )
        
        # 验证反向关系
        self.assertIn(reaction, self.comment.reactions.all())
        self.assertEqual(self.comment.reactions.count(), 1)


class StarRecordModelTest(TestCase):
    """收藏记录模型单元测试
    
    验证需求：6.1
    """
    
    def setUp(self):
        """测试前准备"""
        self.user = Users.objects.create(
            username='testuser',
            email='test@example.com',
            name='测试用户'
        )
        self.kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='描述',
            uploader=self.user
        )
    
    def test_create_star_record(self):
        """测试创建收藏记录"""
        star = StarRecord.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge'
        )
        
        # 验证字段
        self.assertEqual(star.user, self.user)
        self.assertEqual(star.target_id, str(self.kb.id))
        self.assertEqual(star.target_type, 'knowledge')
    
    def test_star_record_str(self):
        """测试字符串表示"""
        star = StarRecord.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge'
        )
        
        str_repr = str(star)
        self.assertIn('testuser', str_repr)
        self.assertIn('收藏了', str_repr)
        self.assertIn('知识库', str_repr)
    
    def test_star_record_unique_constraint(self):
        """测试唯一约束"""
        # 创建第一个收藏记录
        StarRecord.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge'
        )
        
        # 尝试创建重复的收藏记录应该失败
        with self.assertRaises(IntegrityError):
            StarRecord.objects.create(
                user=self.user,
                target_id=str(self.kb.id),
                target_type='knowledge'
            )
    
    def test_star_record_target_types(self):
        """测试不同目标类型的收藏"""
        # 知识库收藏
        star1 = StarRecord.objects.create(
            user=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge'
        )
        self.assertEqual(star1.target_type, 'knowledge')
        
        # 人设卡收藏
        star2 = StarRecord.objects.create(
            user=self.user,
            target_id=str(uuid.uuid4()),
            target_type='persona'
        )
        self.assertEqual(star2.target_type, 'persona')


class EmailVerificationModelTest(TestCase):
    """邮箱验证模型单元测试
    
    验证需求：7.1
    """
    
    def test_create_email_verification(self):
        """测试创建邮箱验证"""
        expires_at = timezone.now() + timedelta(minutes=10)
        verification = EmailVerification.objects.create(
            email='test@example.com',
            code='123456',
            expires_at=expires_at
        )
        
        # 验证字段
        self.assertEqual(verification.email, 'test@example.com')
        self.assertEqual(verification.code, '123456')
        self.assertFalse(verification.is_used)
        self.assertEqual(verification.expires_at, expires_at)
    
    def test_email_verification_str(self):
        """测试字符串表示"""
        expires_at = timezone.now() + timedelta(minutes=10)
        verification = EmailVerification.objects.create(
            email='test@example.com',
            code='654321',
            expires_at=expires_at
        )
        
        str_repr = str(verification)
        self.assertIn('test@example.com', str_repr)
        self.assertIn('654321', str_repr)
    
    def test_email_verification_expiry(self):
        """测试验证码过期查询"""
        # 创建已过期的验证码
        expired_verification = EmailVerification.objects.create(
            email='expired@example.com',
            code='111111',
            expires_at=timezone.now() - timedelta(minutes=10)
        )
        
        # 创建未过期的验证码
        valid_verification = EmailVerification.objects.create(
            email='valid@example.com',
            code='222222',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # 查询过期的验证码
        expired_codes = EmailVerification.objects.filter(
            expires_at__lt=timezone.now()
        )
        self.assertIn(expired_verification, expired_codes)
        self.assertNotIn(valid_verification, expired_codes)
    
    def test_email_verification_usage(self):
        """测试验证码使用状态"""
        verification = EmailVerification.objects.create(
            email='test@example.com',
            code='123456',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # 标记为已使用
        verification.is_used = True
        verification.save()
        
        # 验证状态已更新
        updated = EmailVerification.objects.get(id=verification.id)
        self.assertTrue(updated.is_used)


class UploadRecordModelTest(TestCase):
    """上传记录模型单元测试
    
    验证需求：8.1
    """
    
    def setUp(self):
        """测试前准备"""
        self.user = Users.objects.create(
            username='testuser',
            email='test@example.com',
            name='测试用户'
        )
        self.kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='描述',
            uploader=self.user
        )
    
    def test_create_upload_record(self):
        """测试创建上传记录"""
        record = UploadRecord.objects.create(
            uploader=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            name='测试知识库',
            description='上传描述'
        )
        
        # 验证字段
        self.assertEqual(record.uploader, self.user)
        self.assertEqual(record.target_id, str(self.kb.id))
        self.assertEqual(record.target_type, 'knowledge')
        self.assertEqual(record.name, '测试知识库')
        self.assertEqual(record.description, '上传描述')
        
        # 验证默认状态
        self.assertEqual(record.status, 'pending')
    
    def test_upload_record_str(self):
        """测试字符串表示"""
        record = UploadRecord.objects.create(
            uploader=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            name='测试上传',
            status='approved'
        )
        
        str_repr = str(record)
        self.assertIn('testuser', str_repr)
        self.assertIn('上传了', str_repr)
        self.assertIn('测试上传', str_repr)
        self.assertIn('已通过', str_repr)
    
    def test_upload_record_status_choices(self):
        """测试审核状态选项"""
        # 待审核
        record1 = UploadRecord.objects.create(
            uploader=self.user,
            target_id=str(self.kb.id),
            target_type='knowledge',
            name='待审核',
            status='pending'
        )
        self.assertEqual(record1.status, 'pending')
        
        # 已通过
        record2 = UploadRecord.objects.create(
            uploader=self.user,
            target_id=str(uuid.uuid4()),
            target_type='knowledge',
            name='已通过',
            status='approved'
        )
        self.assertEqual(record2.status, 'approved')
        
        # 已拒绝
        record3 = UploadRecord.objects.create(
            uploader=self.user,
            target_id=str(uuid.uuid4()),
            target_type='knowledge',
            name='已拒绝',
            status='rejected'
        )
        self.assertEqual(record3.status, 'rejected')


class DownloadRecordModelTest(TestCase):
    """下载记录模型单元测试
    
    验证需求：8.2
    """
    
    def setUp(self):
        """测试前准备"""
        self.user = Users.objects.create(
            username='testuser',
            email='test@example.com',
            name='测试用户'
        )
        self.kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='描述',
            uploader=self.user
        )
    
    def test_create_download_record(self):
        """测试创建下载记录"""
        record = DownloadRecord.objects.create(
            target_id=str(self.kb.id),
            target_type='knowledge'
        )
        
        # 验证字段
        self.assertEqual(record.target_id, str(self.kb.id))
        self.assertEqual(record.target_type, 'knowledge')
    
    def test_download_record_str(self):
        """测试字符串表示"""
        record = DownloadRecord.objects.create(
            target_id=str(self.kb.id),
            target_type='knowledge'
        )
        
        str_repr = str(record)
        self.assertIn('下载', str_repr)
        self.assertIn('知识库', str_repr)
    
    def test_download_record_target_types(self):
        """测试不同目标类型的下载记录"""
        # 知识库下载
        record1 = DownloadRecord.objects.create(
            target_id=str(self.kb.id),
            target_type='knowledge'
        )
        self.assertEqual(record1.target_type, 'knowledge')
        
        # 人设卡下载
        record2 = DownloadRecord.objects.create(
            target_id=str(uuid.uuid4()),
            target_type='persona'
        )
        self.assertEqual(record2.target_type, 'persona')
    
    def test_multiple_download_records(self):
        """测试多次下载记录"""
        # 创建多个下载记录
        record1 = DownloadRecord.objects.create(
            target_id=str(self.kb.id),
            target_type='knowledge'
        )
        record2 = DownloadRecord.objects.create(
            target_id=str(self.kb.id),
            target_type='knowledge'
        )
        
        # 验证可以创建多个下载记录（没有唯一约束）
        records = DownloadRecord.objects.filter(
            target_id=str(self.kb.id),
            target_type='knowledge'
        )
        self.assertEqual(records.count(), 2)

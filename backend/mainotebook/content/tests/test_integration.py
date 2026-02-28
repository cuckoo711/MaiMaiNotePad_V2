"""
Content 应用集成测试

测试完整的业务工作流，验证模型之间的交互和关系。
"""

import uuid
from django.test import TestCase
from django.utils import timezone
from mainotebook.system.models import Users
from mainotebook.content.models import (
    KnowledgeBase, KnowledgeBaseFile,
    PersonaCard, PersonaCardFile,
    Comment, CommentReaction,
    StarRecord, UploadRecord, DownloadRecord
)


class KnowledgeBaseWorkflowTest(TestCase):
    """知识库完整工作流集成测试
    
    测试场景：创建用户 → 创建知识库 → 添加文件 → 添加评论 → 收藏 → 下载
    验证所有关系正常工作
    """
    
    def test_complete_knowledge_base_workflow(self):
        """测试知识库完整工作流
        
        工作流步骤：
        1. 创建用户
        2. 创建知识库
        3. 添加文件
        4. 添加评论（包括嵌套评论）
        5. 添加评论反应
        6. 收藏知识库
        7. 记录下载
        8. 验证所有关系
        """
        # 步骤 1: 创建用户
        user = Users.objects.create(
            username='workflow_user',
            email='workflow@example.com',
            name='工作流测试用户'
        )
        self.assertIsNotNone(user.id)
        
        # 步骤 2: 创建知识库
        kb = KnowledgeBase.objects.create(
            name='完整工作流测试知识库',
            description='这是一个用于测试完整工作流的知识库',
            uploader=user,
            content='知识库的详细内容',
            tags='测试,工作流,集成测试',
            copyright_owner='测试版权所有者',
            version='1.0'
        )
        self.assertIsNotNone(kb.id)
        self.assertEqual(kb.uploader, user)
        self.assertTrue(kb.is_pending)
        self.assertFalse(kb.is_public)
        
        # 验证用户与知识库的反向关系
        self.assertIn(kb, user.uploaded_knowledge_bases.all())
        
        # 步骤 3: 添加文件
        file1 = KnowledgeBaseFile.objects.create(
            knowledge_base=kb,
            file_name='document.pdf',
            original_name='文档.pdf',
            file_path='/uploads/knowledge_base/document.pdf',
            file_type='application/pdf',
            file_size=1024000
        )
        
        file2 = KnowledgeBaseFile.objects.create(
            knowledge_base=kb,
            file_name='readme.txt',
            original_name='说明.txt',
            file_path='/uploads/knowledge_base/readme.txt',
            file_type='text/plain',
            file_size=2048
        )
        
        # 验证文件与知识库的关系
        self.assertEqual(kb.files.count(), 2)
        self.assertIn(file1, kb.files.all())
        self.assertIn(file2, kb.files.all())
        
        # 步骤 4: 添加评论（包括嵌套评论）
        # 创建主评论
        main_comment = Comment.objects.create(
            user=user,
            target_id=str(kb.id),
            target_type='knowledge',
            content='这是一个非常好的知识库！'
        )
        self.assertIsNotNone(main_comment.id)
        self.assertEqual(main_comment.target_id, str(kb.id))
        self.assertEqual(main_comment.target_type, 'knowledge')
        
        # 创建回复评论
        reply_comment = Comment.objects.create(
            user=user,
            target_id=str(kb.id),
            target_type='knowledge',
            content='感谢分享！',
            parent=main_comment
        )
        self.assertEqual(reply_comment.parent, main_comment)
        
        # 验证嵌套评论关系
        self.assertIn(reply_comment, main_comment.replies.all())
        self.assertEqual(main_comment.replies.count(), 1)
        
        # 验证评论与用户的关系
        self.assertIn(main_comment, user.comments.all())
        self.assertIn(reply_comment, user.comments.all())
        
        # 步骤 5: 添加评论反应
        reaction = CommentReaction.objects.create(
            user=user,
            comment=main_comment,
            reaction_type='like'
        )
        self.assertIsNotNone(reaction.id)
        self.assertEqual(reaction.reaction_type, 'like')
        
        # 验证反应与评论的关系
        self.assertIn(reaction, main_comment.reactions.all())
        self.assertEqual(main_comment.reactions.count(), 1)
        
        # 步骤 6: 收藏知识库
        star = StarRecord.objects.create(
            user=user,
            target_id=str(kb.id),
            target_type='knowledge'
        )
        self.assertIsNotNone(star.id)
        self.assertEqual(star.target_id, str(kb.id))
        
        # 验证收藏与用户的关系
        self.assertIn(star, user.star_records.all())
        
        # 步骤 7: 记录下载
        download1 = DownloadRecord.objects.create(
            target_id=str(kb.id),
            target_type='knowledge'
        )
        
        download2 = DownloadRecord.objects.create(
            target_id=str(kb.id),
            target_type='knowledge'
        )
        
        # 验证下载记录
        download_records = DownloadRecord.objects.filter(
            target_id=str(kb.id),
            target_type='knowledge'
        )
        self.assertEqual(download_records.count(), 2)
        
        # 步骤 8: 验证所有关系
        # 验证知识库的所有关联数据
        self.assertEqual(kb.files.count(), 2)
        
        kb_comments = Comment.objects.filter(
            target_id=str(kb.id),
            target_type='knowledge'
        )
        self.assertEqual(kb_comments.count(), 2)  # 1个主评论 + 1个回复
        
        kb_stars = StarRecord.objects.filter(
            target_id=str(kb.id),
            target_type='knowledge'
        )
        self.assertEqual(kb_stars.count(), 1)
        
        kb_downloads = DownloadRecord.objects.filter(
            target_id=str(kb.id),
            target_type='knowledge'
        )
        self.assertEqual(kb_downloads.count(), 2)
        
        # 验证用户的所有关联数据
        self.assertEqual(user.uploaded_knowledge_bases.count(), 1)
        self.assertEqual(user.comments.count(), 2)
        self.assertEqual(user.comment_reactions.count(), 1)
        self.assertEqual(user.star_records.count(), 1)
    
    def test_knowledge_base_cascade_delete(self):
        """测试知识库级联删除
        
        验证删除知识库时，相关文件也被删除
        """
        # 创建用户和知识库
        user = Users.objects.create(
            username='cascade_user',
            email='cascade@example.com',
            name='级联测试用户'
        )
        
        kb = KnowledgeBase.objects.create(
            name='级联删除测试知识库',
            description='测试级联删除',
            uploader=user
        )
        
        # 添加文件
        file1 = KnowledgeBaseFile.objects.create(
            knowledge_base=kb,
            file_name='file1.pdf',
            original_name='文件1.pdf',
            file_path='/path/1',
            file_type='application/pdf'
        )
        
        file2 = KnowledgeBaseFile.objects.create(
            knowledge_base=kb,
            file_name='file2.txt',
            original_name='文件2.txt',
            file_path='/path/2',
            file_type='text/plain'
        )
        
        file1_id = file1.id
        file2_id = file2.id
        kb_id = kb.id
        
        # 删除知识库
        kb.delete()
        
        # 验证知识库已删除
        self.assertFalse(KnowledgeBase.objects.filter(id=kb_id).exists())
        
        # 验证文件已被级联删除
        self.assertFalse(KnowledgeBaseFile.objects.filter(id=file1_id).exists())
        self.assertFalse(KnowledgeBaseFile.objects.filter(id=file2_id).exists())
    
    def test_knowledge_base_with_upload_record(self):
        """测试知识库与上传记录的关系"""
        # 创建用户和知识库
        user = Users.objects.create(
            username='upload_user',
            email='upload@example.com',
            name='上传测试用户'
        )
        
        kb = KnowledgeBase.objects.create(
            name='上传记录测试知识库',
            description='测试上传记录',
            uploader=user
        )
        
        # 创建上传记录
        upload_record = UploadRecord.objects.create(
            uploader=user,
            target_id=str(kb.id),
            target_type='knowledge',
            name=kb.name,
            description=kb.description,
            status='pending'
        )
        
        # 验证上传记录
        self.assertEqual(upload_record.uploader, user)
        self.assertEqual(upload_record.target_id, str(kb.id))
        self.assertEqual(upload_record.status, 'pending')
        
        # 模拟审核通过
        upload_record.status = 'approved'
        upload_record.save()
        kb.is_pending = False
        kb.is_public = True
        kb.save()
        
        # 验证状态更新
        updated_record = UploadRecord.objects.get(id=upload_record.id)
        self.assertEqual(updated_record.status, 'approved')
        
        updated_kb = KnowledgeBase.objects.get(id=kb.id)
        self.assertFalse(updated_kb.is_pending)
        self.assertTrue(updated_kb.is_public)


class PersonaCardWorkflowTest(TestCase):
    """人设卡完整工作流集成测试
    
    测试场景：创建用户 → 创建人设卡 → 添加文件 → 添加评论 → 收藏 → 下载
    验证所有关系正常工作
    """
    
    def test_complete_persona_card_workflow(self):
        """测试人设卡完整工作流
        
        工作流步骤：
        1. 创建用户
        2. 创建人设卡
        3. 添加文件
        4. 添加评论（包括嵌套评论）
        5. 添加评论反应
        6. 收藏人设卡
        7. 记录下载
        8. 验证所有关系
        """
        # 步骤 1: 创建用户
        user = Users.objects.create(
            username='persona_workflow_user',
            email='persona_workflow@example.com',
            name='人设卡工作流测试用户'
        )
        self.assertIsNotNone(user.id)
        
        # 步骤 2: 创建人设卡
        pc = PersonaCard.objects.create(
            name='完整工作流测试人设卡',
            description='这是一个用于测试完整工作流的人设卡',
            uploader=user,
            content='人设卡的详细内容',
            tags='测试,工作流,人设卡',
            copyright_owner='测试版权所有者',
            version='1.0'
        )
        self.assertIsNotNone(pc.id)
        self.assertEqual(pc.uploader, user)
        self.assertTrue(pc.is_pending)
        self.assertFalse(pc.is_public)
        
        # 验证用户与人设卡的反向关系
        self.assertIn(pc, user.uploaded_persona_cards.all())
        
        # 步骤 3: 添加文件
        file1 = PersonaCardFile.objects.create(
            persona_card=pc,
            file_name='character.json',
            original_name='角色.json',
            file_path='/uploads/persona_card/character.json',
            file_type='application/json',
            file_size=4096
        )
        
        file2 = PersonaCardFile.objects.create(
            persona_card=pc,
            file_name='avatar.png',
            original_name='头像.png',
            file_path='/uploads/persona_card/avatar.png',
            file_type='image/png',
            file_size=102400
        )
        
        # 验证文件与人设卡的关系
        self.assertEqual(pc.files.count(), 2)
        self.assertIn(file1, pc.files.all())
        self.assertIn(file2, pc.files.all())
        
        # 步骤 4: 添加评论（包括嵌套评论）
        # 创建主评论
        main_comment = Comment.objects.create(
            user=user,
            target_id=str(pc.id),
            target_type='persona',
            content='这个人设卡设计得很棒！'
        )
        self.assertIsNotNone(main_comment.id)
        self.assertEqual(main_comment.target_id, str(pc.id))
        self.assertEqual(main_comment.target_type, 'persona')
        
        # 创建回复评论
        reply_comment = Comment.objects.create(
            user=user,
            target_id=str(pc.id),
            target_type='persona',
            content='非常有创意！',
            parent=main_comment
        )
        self.assertEqual(reply_comment.parent, main_comment)
        
        # 验证嵌套评论关系
        self.assertIn(reply_comment, main_comment.replies.all())
        self.assertEqual(main_comment.replies.count(), 1)
        
        # 验证评论与用户的关系
        self.assertIn(main_comment, user.comments.all())
        self.assertIn(reply_comment, user.comments.all())
        
        # 步骤 5: 添加评论反应
        like_reaction = CommentReaction.objects.create(
            user=user,
            comment=main_comment,
            reaction_type='like'
        )
        self.assertIsNotNone(like_reaction.id)
        self.assertEqual(like_reaction.reaction_type, 'like')
        
        # 验证反应与评论的关系
        self.assertIn(like_reaction, main_comment.reactions.all())
        self.assertEqual(main_comment.reactions.count(), 1)
        
        # 步骤 6: 收藏人设卡
        star = StarRecord.objects.create(
            user=user,
            target_id=str(pc.id),
            target_type='persona'
        )
        self.assertIsNotNone(star.id)
        self.assertEqual(star.target_id, str(pc.id))
        self.assertEqual(star.target_type, 'persona')
        
        # 验证收藏与用户的关系
        self.assertIn(star, user.star_records.all())
        
        # 步骤 7: 记录下载
        download1 = DownloadRecord.objects.create(
            target_id=str(pc.id),
            target_type='persona'
        )
        
        download2 = DownloadRecord.objects.create(
            target_id=str(pc.id),
            target_type='persona'
        )
        
        download3 = DownloadRecord.objects.create(
            target_id=str(pc.id),
            target_type='persona'
        )
        
        # 验证下载记录
        download_records = DownloadRecord.objects.filter(
            target_id=str(pc.id),
            target_type='persona'
        )
        self.assertEqual(download_records.count(), 3)
        
        # 步骤 8: 验证所有关系
        # 验证人设卡的所有关联数据
        self.assertEqual(pc.files.count(), 2)
        
        pc_comments = Comment.objects.filter(
            target_id=str(pc.id),
            target_type='persona'
        )
        self.assertEqual(pc_comments.count(), 2)  # 1个主评论 + 1个回复
        
        pc_stars = StarRecord.objects.filter(
            target_id=str(pc.id),
            target_type='persona'
        )
        self.assertEqual(pc_stars.count(), 1)
        
        pc_downloads = DownloadRecord.objects.filter(
            target_id=str(pc.id),
            target_type='persona'
        )
        self.assertEqual(pc_downloads.count(), 3)
        
        # 验证用户的所有关联数据
        self.assertEqual(user.uploaded_persona_cards.count(), 1)
        self.assertEqual(user.comments.count(), 2)
        self.assertEqual(user.comment_reactions.count(), 1)
        self.assertEqual(user.star_records.count(), 1)
    
    def test_persona_card_cascade_delete(self):
        """测试人设卡级联删除
        
        验证删除人设卡时，相关文件也被删除
        """
        # 创建用户和人设卡
        user = Users.objects.create(
            username='persona_cascade_user',
            email='persona_cascade@example.com',
            name='人设卡级联测试用户'
        )
        
        pc = PersonaCard.objects.create(
            name='级联删除测试人设卡',
            description='测试级联删除',
            uploader=user
        )
        
        # 添加文件
        file1 = PersonaCardFile.objects.create(
            persona_card=pc,
            file_name='file1.json',
            original_name='文件1.json',
            file_path='/path/1',
            file_type='application/json'
        )
        
        file2 = PersonaCardFile.objects.create(
            persona_card=pc,
            file_name='file2.png',
            original_name='文件2.png',
            file_path='/path/2',
            file_type='image/png'
        )
        
        file1_id = file1.id
        file2_id = file2.id
        pc_id = pc.id
        
        # 删除人设卡
        pc.delete()
        
        # 验证人设卡已删除
        self.assertFalse(PersonaCard.objects.filter(id=pc_id).exists())
        
        # 验证文件已被级联删除
        self.assertFalse(PersonaCardFile.objects.filter(id=file1_id).exists())
        self.assertFalse(PersonaCardFile.objects.filter(id=file2_id).exists())
    
    def test_persona_card_with_upload_record(self):
        """测试人设卡与上传记录的关系"""
        # 创建用户和人设卡
        user = Users.objects.create(
            username='persona_upload_user',
            email='persona_upload@example.com',
            name='人设卡上传测试用户'
        )
        
        pc = PersonaCard.objects.create(
            name='上传记录测试人设卡',
            description='测试上传记录',
            uploader=user
        )
        
        # 创建上传记录
        upload_record = UploadRecord.objects.create(
            uploader=user,
            target_id=str(pc.id),
            target_type='persona',
            name=pc.name,
            description=pc.description,
            status='pending'
        )
        
        # 验证上传记录
        self.assertEqual(upload_record.uploader, user)
        self.assertEqual(upload_record.target_id, str(pc.id))
        self.assertEqual(upload_record.target_type, 'persona')
        self.assertEqual(upload_record.status, 'pending')
        
        # 模拟审核拒绝
        upload_record.status = 'rejected'
        upload_record.save()
        pc.rejection_reason = '内容不符合规范'
        pc.save()
        
        # 验证状态更新
        updated_record = UploadRecord.objects.get(id=upload_record.id)
        self.assertEqual(updated_record.status, 'rejected')
        
        updated_pc = PersonaCard.objects.get(id=pc.id)
        self.assertEqual(updated_pc.rejection_reason, '内容不符合规范')
        self.assertTrue(updated_pc.is_pending)


class CrossModelInteractionTest(TestCase):
    """跨模型交互测试
    
    测试知识库和人设卡之间的交互场景
    """
    
    def test_user_with_multiple_content_types(self):
        """测试用户同时拥有知识库和人设卡"""
        # 创建用户
        user = Users.objects.create(
            username='multi_content_user',
            email='multi@example.com',
            name='多内容用户'
        )
        
        # 创建多个知识库
        kb1 = KnowledgeBase.objects.create(
            name='知识库1',
            description='描述1',
            uploader=user
        )
        
        kb2 = KnowledgeBase.objects.create(
            name='知识库2',
            description='描述2',
            uploader=user
        )
        
        # 创建多个人设卡
        pc1 = PersonaCard.objects.create(
            name='人设卡1',
            description='描述1',
            uploader=user
        )
        
        pc2 = PersonaCard.objects.create(
            name='人设卡2',
            description='描述2',
            uploader=user
        )
        
        # 验证用户的所有上传内容
        self.assertEqual(user.uploaded_knowledge_bases.count(), 2)
        self.assertEqual(user.uploaded_persona_cards.count(), 2)
        
        # 收藏所有内容
        StarRecord.objects.create(
            user=user,
            target_id=str(kb1.id),
            target_type='knowledge'
        )
        
        StarRecord.objects.create(
            user=user,
            target_id=str(kb2.id),
            target_type='knowledge'
        )
        
        StarRecord.objects.create(
            user=user,
            target_id=str(pc1.id),
            target_type='persona'
        )
        
        StarRecord.objects.create(
            user=user,
            target_id=str(pc2.id),
            target_type='persona'
        )
        
        # 验证收藏记录
        self.assertEqual(user.star_records.count(), 4)
        
        # 按类型查询收藏
        kb_stars = user.star_records.filter(target_type='knowledge')
        pc_stars = user.star_records.filter(target_type='persona')
        
        self.assertEqual(kb_stars.count(), 2)
        self.assertEqual(pc_stars.count(), 2)
    
    def test_comment_on_different_target_types(self):
        """测试对不同目标类型的评论"""
        # 创建用户
        user = Users.objects.create(
            username='comment_user',
            email='comment@example.com',
            name='评论用户'
        )
        
        # 创建知识库和人设卡
        kb = KnowledgeBase.objects.create(
            name='测试知识库',
            description='描述',
            uploader=user
        )
        
        pc = PersonaCard.objects.create(
            name='测试人设卡',
            description='描述',
            uploader=user
        )
        
        # 对知识库评论
        kb_comment = Comment.objects.create(
            user=user,
            target_id=str(kb.id),
            target_type='knowledge',
            content='知识库评论'
        )
        
        # 对人设卡评论
        pc_comment = Comment.objects.create(
            user=user,
            target_id=str(pc.id),
            target_type='persona',
            content='人设卡评论'
        )
        
        # 验证评论
        self.assertEqual(user.comments.count(), 2)
        
        # 按目标类型查询评论
        kb_comments = Comment.objects.filter(
            target_id=str(kb.id),
            target_type='knowledge'
        )
        pc_comments = Comment.objects.filter(
            target_id=str(pc.id),
            target_type='persona'
        )
        
        self.assertEqual(kb_comments.count(), 1)
        self.assertEqual(pc_comments.count(), 1)
        self.assertEqual(kb_comments.first().content, '知识库评论')
        self.assertEqual(pc_comments.first().content, '人设卡评论')
    
    def test_download_statistics(self):
        """测试下载统计功能"""
        # 创建用户
        user = Users.objects.create(
            username='download_user',
            email='download@example.com',
            name='下载用户'
        )
        
        # 创建知识库
        kb = KnowledgeBase.objects.create(
            name='热门知识库',
            description='描述',
            uploader=user
        )
        
        # 创建人设卡
        pc = PersonaCard.objects.create(
            name='热门人设卡',
            description='描述',
            uploader=user
        )
        
        # 模拟多次下载
        for _ in range(5):
            DownloadRecord.objects.create(
                target_id=str(kb.id),
                target_type='knowledge'
            )
        
        for _ in range(3):
            DownloadRecord.objects.create(
                target_id=str(pc.id),
                target_type='persona'
            )
        
        # 统计下载次数
        kb_downloads = DownloadRecord.objects.filter(
            target_id=str(kb.id),
            target_type='knowledge'
        ).count()
        
        pc_downloads = DownloadRecord.objects.filter(
            target_id=str(pc.id),
            target_type='persona'
        ).count()
        
        self.assertEqual(kb_downloads, 5)
        self.assertEqual(pc_downloads, 3)
        
        # 更新下载计数
        kb.downloads = kb_downloads
        kb.save()
        
        pc.downloads = pc_downloads
        pc.save()
        
        # 验证更新
        updated_kb = KnowledgeBase.objects.get(id=kb.id)
        updated_pc = PersonaCard.objects.get(id=pc.id)
        
        self.assertEqual(updated_kb.downloads, 5)
        self.assertEqual(updated_pc.downloads, 3)

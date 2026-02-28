"""人设卡服务单元测试

测试人设卡服务的各项功能，包括：
- 创建人设卡（验证必填字段、名称唯一性）
- TOML 文件验证（必须包含且仅包含一个 bot_config.toml）
- 提交审核（权限验证、状态验证、TOML 验证）
- 更新人设卡（权限验证）
- 删除人设卡（权限验证、软删除）
- 获取公开人设卡列表
- 获取用户人设卡列表

验证需求：2.1, 2.8, 2.12, 2.13, 2.16
"""

from django.test import TestCase
from django.core.exceptions import ValidationError, PermissionDenied
from mainotebook.system.models import Users
from ..models import PersonaCard, PersonaCardFile, StarRecord, UploadRecord
from ..services.persona_card_service import PersonaCardService
import tempfile
import os


class PersonaCardServiceTest(TestCase):
    """人设卡服务单元测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建测试用户
        self.user1 = Users.objects.create(
            username="testuser1",
            name="测试用户1",
            email="test1@example.com"
        )
        self.user2 = Users.objects.create(
            username="testuser2",
            name="测试用户2",
            email="test2@example.com"
        )
        
        # 创建临时目录用于测试文件
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后清理"""
        # 清理测试数据
        PersonaCardFile.objects.all().delete()
        PersonaCard.objects.all().delete()
        UploadRecord.objects.all().delete()
        StarRecord.objects.all().delete()
        Users.objects.all().delete()
        
        # 清理临时文件
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _create_toml_file(self, persona_card, filename='bot_config.toml', content=None):
        """辅助方法：创建 TOML 文件
        
        Args:
            persona_card: 人设卡对象
            filename: 文件名
            content: TOML 文件内容，默认为有效的 TOML
        """
        if content is None:
            content = 'version = "1.0"\n'
        
        # 创建临时文件
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 创建文件记录
        PersonaCardFile.objects.create(
            persona_card=persona_card,
            file_name=filename,
            original_name=filename,
            file_path=file_path,
            file_type='application/toml',
            file_size=len(content.encode('utf-8'))
        )
        
        return file_path
    
    # ========== 创建人设卡测试 ==========
    
    def test_create_persona_card_with_valid_data(self):
        """测试使用有效数据创建人设卡（需求 2.1）"""
        data = {
            'name': '测试人设卡',
            'description': '这是一个测试人设卡',
            'tags': 'AI,助手',
            'version': '1.0'
        }
        
        pc = PersonaCardService.create_persona_card(self.user1, data)
        
        # 验证人设卡创建成功
        self.assertIsNotNone(pc)
        self.assertEqual(pc.name, '测试人设卡')
        self.assertEqual(pc.description, '这是一个测试人设卡')
        self.assertEqual(pc.uploader, self.user1)
        self.assertEqual(pc.tags, 'AI,助手')
        self.assertEqual(pc.version, '1.0')
        self.assertTrue(pc.is_pending)  # 默认待审核
        self.assertFalse(pc.is_public)  # 默认不公开
        
        # 验证上传记录创建成功
        upload_record = UploadRecord.objects.filter(
            target_id=str(pc.id),
            target_type='persona'
        ).first()
        self.assertIsNotNone(upload_record)
        self.assertEqual(upload_record.uploader, self.user1)
        self.assertEqual(upload_record.name, '测试人设卡')
        self.assertEqual(upload_record.status, 'pending')
    
    def test_create_persona_card_with_duplicate_name(self):
        """测试创建同名人设卡应该失败（需求 2.1）"""
        data = {
            'name': '重复名称人设卡',
            'description': '第一个人设卡'
        }
        
        # 第一次创建成功
        pc1 = PersonaCardService.create_persona_card(self.user1, data)
        self.assertIsNotNone(pc1)
        
        # 第二次创建应该失败（同一用户）
        with self.assertRaises(ValidationError) as context:
            PersonaCardService.create_persona_card(self.user1, data)
        
        self.assertIn("同名", str(context.exception))
    
    def test_create_persona_card_with_same_name_different_user(self):
        """测试不同用户可以创建同名人设卡（需求 2.1）"""
        data = {
            'name': '相同名称',
            'description': '测试描述'
        }
        
        # 用户1创建
        pc1 = PersonaCardService.create_persona_card(self.user1, data)
        self.assertIsNotNone(pc1)
        
        # 用户2创建同名人设卡应该成功
        pc2 = PersonaCardService.create_persona_card(self.user2, data)
        self.assertIsNotNone(pc2)
        self.assertEqual(pc1.name, pc2.name)
        self.assertNotEqual(pc1.uploader, pc2.uploader)
    
    # ========== TOML 文件验证测试 ==========
    
    def test_validate_toml_file_with_valid_file(self):
        """测试验证有效的 TOML 文件（需求 2.12, 2.13）"""
        # 创建人设卡
        pc = PersonaCard.objects.create(
            name='测试人设卡',
            description='描述',
            uploader=self.user1
        )
        
        # 添加有效的 bot_config.toml 文件
        self._create_toml_file(pc, 'bot_config.toml', 'version = "1.0"\n')
        
        # 验证 TOML 文件
        is_valid, error_msg = PersonaCardService.validate_toml_file(pc)
        
        # 验证结果
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, '')
    
    def test_validate_toml_file_missing(self):
        """测试验证缺少 TOML 文件的人设卡（需求 2.12）"""
        # 创建人设卡（没有文件）
        pc = PersonaCard.objects.create(
            name='测试人设卡',
            description='描述',
            uploader=self.user1
        )
        
        # 验证 TOML 文件
        is_valid, error_msg = PersonaCardService.validate_toml_file(pc)
        
        # 验证结果
        self.assertFalse(is_valid)
        self.assertIn("必须包含", error_msg)
        self.assertIn("bot_config.toml", error_msg)
    
    def test_validate_toml_file_multiple_files(self):
        """测试验证包含多个 TOML 文件的人设卡（需求 2.12）"""
        # 创建人设卡
        pc = PersonaCard.objects.create(
            name='测试人设卡',
            description='描述',
            uploader=self.user1
        )
        
        # 添加两个 bot_config.toml 文件
        self._create_toml_file(pc, 'bot_config.toml', 'version = "1.0"\n')
        self._create_toml_file(pc, 'bot_config.toml', 'version = "2.0"\n')
        
        # 验证 TOML 文件
        is_valid, error_msg = PersonaCardService.validate_toml_file(pc)
        
        # 验证结果
        self.assertFalse(is_valid)
        self.assertIn("只能包含一个", error_msg)
        self.assertIn("bot_config.toml", error_msg)
    
    def test_validate_toml_file_invalid_syntax(self):
        """测试验证语法错误的 TOML 文件（需求 2.16）"""
        # 创建人设卡
        pc = PersonaCard.objects.create(
            name='测试人设卡',
            description='描述',
            uploader=self.user1
        )
        
        # 添加语法错误的 TOML 文件
        invalid_toml = 'version = "1.0\n'  # 缺少结束引号
        self._create_toml_file(pc, 'bot_config.toml', invalid_toml)
        
        # 验证 TOML 文件
        is_valid, error_msg = PersonaCardService.validate_toml_file(pc)
        
        # 验证结果
        self.assertFalse(is_valid)
        # 错误消息应该包含 TOML 相关的错误提示
        self.assertTrue(
            "TOML" in error_msg or "语法" in error_msg or "错误" in error_msg,
            f"错误消息应该提示 TOML 语法错误，实际消息：{error_msg}"
        )
    
    def test_validate_toml_file_missing_version_field(self):
        """测试验证缺少 version 字段的 TOML 文件（需求 2.13）"""
        # 创建人设卡
        pc = PersonaCard.objects.create(
            name='测试人设卡',
            description='描述',
            uploader=self.user1
        )
        
        # 添加缺少 version 字段的 TOML 文件
        invalid_toml = 'name = "test"\n'  # 没有 version 字段
        self._create_toml_file(pc, 'bot_config.toml', invalid_toml)
        
        # 验证 TOML 文件
        is_valid, error_msg = PersonaCardService.validate_toml_file(pc)
        
        # 验证结果
        self.assertFalse(is_valid)
        # 错误消息应该提示缺少 version 字段
        self.assertTrue(
            "version" in error_msg.lower() or "字段" in error_msg,
            f"错误消息应该提示缺少 version 字段，实际消息：{error_msg}"
        )
    
    # ========== 提交审核测试 ==========
    
    def test_submit_for_review_with_valid_toml(self):
        """测试提交包含有效 TOML 文件的人设卡审核（需求 2.8, 2.12, 2.13）"""
        # 创建人设卡（未提交审核）
        pc = PersonaCard.objects.create(
            name='待审核人设卡',
            description='描述',
            uploader=self.user1,
            is_pending=False,
            is_public=False
        )
        
        # 添加有效的 TOML 文件
        self._create_toml_file(pc, 'bot_config.toml', 'version = "1.0"\n')
        
        # 创建上传记录
        UploadRecord.objects.create(
            uploader=self.user1,
            target_id=str(pc.id),
            target_type='persona',
            name=pc.name,
            description=pc.description,
            status='approved'  # 初始状态
        )
        
        # 提交审核
        PersonaCardService.submit_for_review(pc, self.user1)
        
        # 验证状态更新
        pc.refresh_from_db()
        self.assertTrue(pc.is_pending)
        self.assertFalse(pc.is_public)
        
        # 验证上传记录状态更新
        upload_record = UploadRecord.objects.get(
            target_id=str(pc.id),
            target_type='persona'
        )
        self.assertEqual(upload_record.status, 'pending')
    
    def test_submit_for_review_without_toml(self):
        """测试提交缺少 TOML 文件的人设卡审核应该失败（需求 2.12, 2.16）"""
        # 创建人设卡（没有 TOML 文件）
        pc = PersonaCard.objects.create(
            name='缺少TOML的人设卡',
            description='描述',
            uploader=self.user1,
            is_pending=False
        )
        
        # 尝试提交审核
        with self.assertRaises(ValidationError) as context:
            PersonaCardService.submit_for_review(pc, self.user1)
        
        # 验证错误消息
        self.assertIn("必须包含", str(context.exception))
        self.assertIn("bot_config.toml", str(context.exception))
        
        # 验证状态未改变
        pc.refresh_from_db()
        self.assertFalse(pc.is_pending)
    
    def test_submit_for_review_with_invalid_toml(self):
        """测试提交包含无效 TOML 文件的人设卡审核应该失败（需求 2.16）"""
        # 创建人设卡
        pc = PersonaCard.objects.create(
            name='无效TOML的人设卡',
            description='描述',
            uploader=self.user1,
            is_pending=False
        )
        
        # 添加无效的 TOML 文件（缺少 version 字段）
        self._create_toml_file(pc, 'bot_config.toml', 'name = "test"\n')
        
        # 尝试提交审核
        with self.assertRaises(ValidationError) as context:
            PersonaCardService.submit_for_review(pc, self.user1)
        
        # 验证错误消息
        error_msg = str(context.exception)
        self.assertTrue(
            "version" in error_msg.lower() or "字段" in error_msg or "验证失败" in error_msg,
            f"错误消息应该提示 TOML 验证失败，实际消息：{error_msg}"
        )
        
        # 验证状态未改变
        pc.refresh_from_db()
        self.assertFalse(pc.is_pending)
    
    def test_submit_for_review_by_non_owner(self):
        """测试非创建者提交审核应该失败（需求 2.8）"""
        # 用户1创建人设卡
        pc = PersonaCard.objects.create(
            name='用户1的人设卡',
            description='描述',
            uploader=self.user1,
            is_pending=False
        )
        
        # 添加有效的 TOML 文件
        self._create_toml_file(pc, 'bot_config.toml', 'version = "1.0"\n')
        
        # 用户2尝试提交审核
        with self.assertRaises(PermissionDenied) as context:
            PersonaCardService.submit_for_review(pc, self.user2)
        
        self.assertIn("创建者", str(context.exception))
        
        # 验证状态未改变
        pc.refresh_from_db()
        self.assertFalse(pc.is_pending)
    
    def test_submit_for_review_already_pending(self):
        """测试重复提交审核应该失败（需求 2.8）"""
        # 创建已处于待审核状态的人设卡
        pc = PersonaCard.objects.create(
            name='已待审核人设卡',
            description='描述',
            uploader=self.user1,
            is_pending=True
        )
        
        # 添加有效的 TOML 文件
        self._create_toml_file(pc, 'bot_config.toml', 'version = "1.0"\n')
        
        # 尝试再次提交审核
        with self.assertRaises(ValidationError) as context:
            PersonaCardService.submit_for_review(pc, self.user1)
        
        self.assertIn("待审核", str(context.exception))
    
    # ========== 更新人设卡测试 ==========
    
    def test_update_persona_card_by_owner(self):
        """测试创建者更新人设卡应该成功（需求 2.1）"""
        # 创建人设卡
        pc = PersonaCard.objects.create(
            name='原始名称',
            description='原始描述',
            uploader=self.user1
        )
        
        # 更新数据
        update_data = {
            'name': '更新后的名称',
            'description': '更新后的描述',
            'tags': '新标签'
        }
        
        updated_pc = PersonaCardService.update_persona_card(
            pc, self.user1, update_data
        )
        
        # 验证更新成功
        self.assertEqual(updated_pc.name, '更新后的名称')
        self.assertEqual(updated_pc.description, '更新后的描述')
        self.assertEqual(updated_pc.tags, '新标签')
    
    def test_update_persona_card_by_non_owner(self):
        """测试非创建者更新人设卡应该失败（需求 2.1）"""
        # 用户1创建人设卡
        pc = PersonaCard.objects.create(
            name='用户1的人设卡',
            description='描述',
            uploader=self.user1
        )
        
        # 用户2尝试更新
        update_data = {
            'name': '恶意更新',
            'description': '恶意描述'
        }
        
        with self.assertRaises(PermissionDenied) as context:
            PersonaCardService.update_persona_card(pc, self.user2, update_data)
        
        self.assertIn("创建者", str(context.exception))
        
        # 验证人设卡未被修改
        pc.refresh_from_db()
        self.assertEqual(pc.name, '用户1的人设卡')
        self.assertEqual(pc.description, '描述')
    
    # ========== 删除人设卡测试 ==========
    
    def test_delete_persona_card_by_owner(self):
        """测试创建者删除人设卡应该成功（需求 2.1）"""
        # 创建人设卡
        pc = PersonaCard.objects.create(
            name='待删除人设卡',
            description='描述',
            uploader=self.user1
        )
        pc_id = pc.id
        
        # 创建收藏记录
        StarRecord.objects.create(
            user=self.user2,
            target_id=str(pc_id),
            target_type='persona'
        )
        
        # 删除人设卡
        PersonaCardService.delete_persona_card(pc, self.user1)
        
        # 验证人设卡被删除
        self.assertFalse(PersonaCard.objects.filter(id=pc_id).exists())
        
        # 验证关联的收藏记录被删除
        star_count = StarRecord.objects.filter(
            target_id=str(pc_id),
            target_type='persona'
        ).count()
        self.assertEqual(star_count, 0)
    
    def test_delete_persona_card_by_non_owner(self):
        """测试非创建者删除人设卡应该失败（需求 2.1）"""
        # 用户1创建人设卡
        pc = PersonaCard.objects.create(
            name='用户1的人设卡',
            description='描述',
            uploader=self.user1
        )
        pc_id = pc.id
        
        # 用户2尝试删除
        with self.assertRaises(PermissionDenied) as context:
            PersonaCardService.delete_persona_card(pc, self.user2)
        
        self.assertIn("创建者", str(context.exception))
        
        # 验证人设卡未被删除
        self.assertTrue(PersonaCard.objects.filter(id=pc_id).exists())
    
    # ========== 获取人设卡列表测试 ==========
    
    def test_get_public_persona_cards(self):
        """测试获取公开人设卡列表"""
        # 创建多个人设卡
        pc1 = PersonaCard.objects.create(
            name='公开人设卡1',
            description='描述1',
            uploader=self.user1,
            is_public=True,
            is_pending=False
        )
        pc2 = PersonaCard.objects.create(
            name='公开人设卡2',
            description='描述2',
            uploader=self.user1,
            is_public=True,
            is_pending=False
        )
        # 私有人设卡（不应出现在结果中）
        PersonaCard.objects.create(
            name='私有人设卡',
            description='描述',
            uploader=self.user1,
            is_public=False,
            is_pending=False
        )
        # 待审核人设卡（不应出现在结果中）
        PersonaCard.objects.create(
            name='待审核人设卡',
            description='描述',
            uploader=self.user1,
            is_public=True,
            is_pending=True
        )
        
        # 获取公开人设卡
        queryset = PersonaCardService.get_public_persona_cards()
        
        # 验证结果
        self.assertEqual(queryset.count(), 2)
        pc_ids = [pc.id for pc in queryset]
        self.assertIn(pc1.id, pc_ids)
        self.assertIn(pc2.id, pc_ids)
    
    def test_get_public_persona_cards_with_search(self):
        """测试搜索公开人设卡"""
        # 创建人设卡
        PersonaCard.objects.create(
            name='AI助手',
            description='智能对话助手',
            tags='AI,助手',
            uploader=self.user1,
            is_public=True,
            is_pending=False
        )
        PersonaCard.objects.create(
            name='翻译机器人',
            description='多语言翻译',
            tags='翻译,语言',
            uploader=self.user1,
            is_public=True,
            is_pending=False
        )
        
        # 搜索包含 "AI" 的人设卡
        queryset = PersonaCardService.get_public_persona_cards(
            filters={'search': 'AI'}
        )
        
        # 验证结果
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().name, 'AI助手')
    
    def test_get_user_persona_cards(self):
        """测试获取用户的人设卡列表"""
        # 用户1创建人设卡
        pc1 = PersonaCard.objects.create(
            name='用户1人设卡1',
            description='描述',
            uploader=self.user1
        )
        pc2 = PersonaCard.objects.create(
            name='用户1人设卡2',
            description='描述',
            uploader=self.user1
        )
        # 用户2创建人设卡（不应出现在用户1的列表中）
        PersonaCard.objects.create(
            name='用户2人设卡',
            description='描述',
            uploader=self.user2
        )
        
        # 获取用户1的人设卡
        queryset = PersonaCardService.get_user_persona_cards(self.user1)
        
        # 验证结果
        self.assertEqual(queryset.count(), 2)
        pc_ids = [pc.id for pc in queryset]
        self.assertIn(pc1.id, pc_ids)
        self.assertIn(pc2.id, pc_ids)

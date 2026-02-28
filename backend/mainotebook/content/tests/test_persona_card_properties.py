"""人设卡属性测试模块

使用 Hypothesis 进行基于属性的测试，验证人设卡管理的核心属性。

**Validates: Requirements 2.12**
"""

import os
import uuid
import tempfile
from django.core.exceptions import ValidationError
from hypothesis import given, settings, strategies as st, assume
from hypothesis.extra.django import TestCase

from mainotebook.system.models import Users
from mainotebook.content.models import PersonaCard, PersonaCardFile
from mainotebook.content.services.persona_card_service import PersonaCardService


# 配置 Hypothesis
settings.register_profile("default", max_examples=100, deadline=None)
settings.load_profile("default")


# 自定义策略：生成有效的人设卡名称
valid_pc_name = st.text(
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='_- '
    ),
    min_size=1,
    max_size=200
).filter(lambda x: x.strip() != '')

# 自定义策略：生成有效的描述
valid_description = st.text(
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'P', 'Z'),
    ),
    min_size=1,
    max_size=1000
).filter(lambda x: x.strip() != '')

# 自定义策略：生成有效的 TOML 内容
valid_toml_content = st.text(
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        max_codepoint=127  # 仅 ASCII 字符
    ),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip() != '' and x.isascii()).map(
    lambda version: f'version = "{version}"'
)


class PersonaCardTOMLFilePropertyTest(TestCase):
    """人设卡 TOML 文件属性测试
    
    **属性 11：人设卡包含唯一 TOML 文件**
    **Validates: Requirements 2.12**
    
    验证人设卡的 TOML 文件约束：
    - 人设卡必须包含且仅包含一个 bot_config.toml 文件
    - 没有 TOML 文件的人设卡验证应失败
    - 包含多个 TOML 文件的人设卡验证应失败
    - 包含一个有效 TOML 文件的人设卡验证应成功
    """
    
    def setUp(self):
        """测试前准备：创建临时目录用于存储测试文件"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后清理：删除临时文件和目录"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @given(
        name=valid_pc_name,
        description=valid_description,
        toml_content=valid_toml_content
    )
    @settings(max_examples=100, deadline=None)
    def test_property_11_persona_card_must_have_exactly_one_toml_file(
        self,
        name,
        description,
        toml_content
    ):
        """属性 11：人设卡必须包含且仅包含一个 TOML 文件
        
        **Validates: Requirements 2.12**
        
        对于任意人设卡，其关联的 bot_config.toml 文件数量应该恰好为 1，
        多于或少于 1 个都应该导致验证失败。
        """
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        
        # 创建人设卡
        persona_card = PersonaCardService.create_persona_card(user, {
            'name': name,
            'description': description
        })
        
        # 场景 1：没有 TOML 文件 - 验证应失败
        is_valid, error_msg = PersonaCardService.validate_toml_file(persona_card)
        self.assertFalse(
            is_valid,
            "没有 TOML 文件的人设卡验证应失败"
        )
        self.assertIn(
            "必须包含",
            error_msg,
            "错误消息应提示缺少 TOML 文件"
        )
        
        # 场景 2：添加一个有效的 TOML 文件 - 验证应成功
        # 创建临时 TOML 文件
        toml_file_path = os.path.join(self.temp_dir, 'bot_config.toml')
        with open(toml_file_path, 'w', encoding='utf-8') as f:
            f.write(toml_content)
        
        # 创建文件记录
        toml_file = PersonaCardFile.objects.create(
            persona_card=persona_card,
            file_name=f'bot_config_{uuid.uuid4().hex[:8]}.toml',
            original_name='bot_config.toml',
            file_path=toml_file_path,
            file_type='application/toml',
            file_size=len(toml_content)
        )
        
        # 验证应成功
        is_valid, error_msg = PersonaCardService.validate_toml_file(persona_card)
        self.assertTrue(
            is_valid,
            f"包含一个有效 TOML 文件的人设卡验证应成功，错误: {error_msg}"
        )
        self.assertEqual(
            error_msg,
            "",
            "验证成功时错误消息应为空"
        )
        
        # 场景 3：添加第二个 TOML 文件 - 验证应失败
        # 创建第二个临时 TOML 文件
        toml_file_path_2 = os.path.join(self.temp_dir, 'bot_config_2.toml')
        with open(toml_file_path_2, 'w', encoding='utf-8') as f:
            f.write(toml_content)
        
        # 创建第二个文件记录
        PersonaCardFile.objects.create(
            persona_card=persona_card,
            file_name=f'bot_config_{uuid.uuid4().hex[:8]}.toml',
            original_name='bot_config.toml',
            file_path=toml_file_path_2,
            file_type='application/toml',
            file_size=len(toml_content)
        )
        
        # 验证应失败
        is_valid, error_msg = PersonaCardService.validate_toml_file(persona_card)
        self.assertFalse(
            is_valid,
            "包含多个 TOML 文件的人设卡验证应失败"
        )
        self.assertIn(
            "只能包含一个",
            error_msg,
            "错误消息应提示 TOML 文件过多"
        )
    
    @given(
        name=valid_pc_name,
        description=valid_description,
        toml_content=valid_toml_content
    )
    @settings(max_examples=100, deadline=None)
    def test_property_11_toml_file_count_is_exactly_one(
        self,
        name,
        description,
        toml_content
    ):
        """属性 11：TOML 文件数量必须恰好为 1
        
        **Validates: Requirements 2.12**
        
        对于任意包含有效 TOML 文件的人设卡，
        其 bot_config.toml 文件数量应该恰好为 1。
        """
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        
        # 创建人设卡
        persona_card = PersonaCardService.create_persona_card(user, {
            'name': name,
            'description': description
        })
        
        # 创建临时 TOML 文件
        toml_file_path = os.path.join(self.temp_dir, 'bot_config.toml')
        with open(toml_file_path, 'w', encoding='utf-8') as f:
            f.write(toml_content)
        
        # 创建文件记录
        PersonaCardFile.objects.create(
            persona_card=persona_card,
            file_name=f'bot_config_{uuid.uuid4().hex[:8]}.toml',
            original_name='bot_config.toml',
            file_path=toml_file_path,
            file_type='application/toml',
            file_size=len(toml_content)
        )
        
        # 断言：TOML 文件数量应该恰好为 1
        toml_file_count = persona_card.files.filter(
            original_name='bot_config.toml'
        ).count()
        self.assertEqual(
            toml_file_count,
            1,
            "人设卡应该包含且仅包含一个 bot_config.toml 文件"
        )
        
        # 断言：验证应成功
        is_valid, error_msg = PersonaCardService.validate_toml_file(persona_card)
        self.assertTrue(
            is_valid,
            f"包含恰好一个 TOML 文件的人设卡验证应成功，错误: {error_msg}"
        )
    
    @given(
        name=valid_pc_name,
        description=valid_description,
        toml_content=valid_toml_content
    )
    @settings(max_examples=100, deadline=None)
    def test_property_11_submit_review_requires_valid_toml(
        self,
        name,
        description,
        toml_content
    ):
        """属性 11：提交审核要求有效的 TOML 文件
        
        **Validates: Requirements 2.12**
        
        对于任意人设卡，提交审核时必须包含有效的 TOML 文件，
        否则提交应失败。
        """
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        
        # 创建人设卡（初始状态为待审核）
        persona_card = PersonaCardService.create_persona_card(user, {
            'name': name,
            'description': description
        })
        
        # 模拟审核通过（手动设置状态）
        persona_card.is_pending = False
        persona_card.is_public = True
        persona_card.save()
        
        # 场景 1：没有 TOML 文件 - 提交审核应失败
        with self.assertRaises(
            ValidationError,
            msg="没有 TOML 文件时提交审核应失败"
        ) as context:
            PersonaCardService.submit_for_review(persona_card, user)
        
        # 验证错误消息
        error_message = str(context.exception)
        self.assertIn(
            "必须包含",
            error_message,
            "错误消息应提示缺少 TOML 文件"
        )
        
        # 场景 2：添加有效的 TOML 文件 - 提交审核应成功
        # 创建临时 TOML 文件
        toml_file_path = os.path.join(self.temp_dir, 'bot_config.toml')
        with open(toml_file_path, 'w', encoding='utf-8') as f:
            f.write(toml_content)
        
        # 创建文件记录
        PersonaCardFile.objects.create(
            persona_card=persona_card,
            file_name=f'bot_config_{uuid.uuid4().hex[:8]}.toml',
            original_name='bot_config.toml',
            file_path=toml_file_path,
            file_type='application/toml',
            file_size=len(toml_content)
        )
        
        # 提交审核应成功
        try:
            PersonaCardService.submit_for_review(persona_card, user)
            persona_card.refresh_from_db()
            
            # 断言：状态应被更新
            self.assertTrue(
                persona_card.is_pending,
                "提交审核后应处于待审核状态"
            )
            self.assertFalse(
                persona_card.is_public,
                "提交审核后不应公开"
            )
        except ValidationError as e:
            self.fail(f"包含有效 TOML 文件时提交审核应成功，但失败了: {str(e)}")
    
    @given(
        name=valid_pc_name,
        description=valid_description
    )
    @settings(max_examples=100, deadline=None)
    def test_property_11_zero_toml_files_fails_validation(
        self,
        name,
        description
    ):
        """属性 11：零个 TOML 文件验证失败
        
        **Validates: Requirements 2.12**
        
        对于任意不包含 bot_config.toml 文件的人设卡，
        验证应失败并返回明确的错误消息。
        """
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        
        # 创建人设卡（不添加任何文件）
        persona_card = PersonaCardService.create_persona_card(user, {
            'name': name,
            'description': description
        })
        
        # 验证 TOML 文件数量为 0
        toml_file_count = persona_card.files.filter(
            original_name='bot_config.toml'
        ).count()
        self.assertEqual(
            toml_file_count,
            0,
            "人设卡不应包含任何 TOML 文件"
        )
        
        # 验证应失败
        is_valid, error_msg = PersonaCardService.validate_toml_file(persona_card)
        self.assertFalse(
            is_valid,
            "不包含 TOML 文件的人设卡验证应失败"
        )
        self.assertIsNotNone(
            error_msg,
            "验证失败时应返回错误消息"
        )
        self.assertTrue(
            len(error_msg) > 0,
            "错误消息不应为空"
        )
        self.assertIn(
            "必须包含",
            error_msg,
            "错误消息应明确指出缺少 TOML 文件"
        )
    
    @given(
        name=valid_pc_name,
        description=valid_description,
        toml_content=valid_toml_content,
        file_count=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_11_multiple_toml_files_fails_validation(
        self,
        name,
        description,
        toml_content,
        file_count
    ):
        """属性 11：多个 TOML 文件验证失败
        
        **Validates: Requirements 2.12**
        
        对于任意包含多个 bot_config.toml 文件的人设卡，
        验证应失败并返回明确的错误消息。
        """
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        
        # 创建人设卡
        persona_card = PersonaCardService.create_persona_card(user, {
            'name': name,
            'description': description
        })
        
        # 创建多个 TOML 文件
        for i in range(file_count):
            # 创建临时 TOML 文件
            toml_file_path = os.path.join(
                self.temp_dir,
                f'bot_config_{i}.toml'
            )
            with open(toml_file_path, 'w', encoding='utf-8') as f:
                f.write(toml_content)
            
            # 创建文件记录（所有文件的 original_name 都是 bot_config.toml）
            PersonaCardFile.objects.create(
                persona_card=persona_card,
                file_name=f'bot_config_{uuid.uuid4().hex[:8]}.toml',
                original_name='bot_config.toml',
                file_path=toml_file_path,
                file_type='application/toml',
                file_size=len(toml_content)
            )
        
        # 验证 TOML 文件数量大于 1
        toml_file_count = persona_card.files.filter(
            original_name='bot_config.toml'
        ).count()
        self.assertEqual(
            toml_file_count,
            file_count,
            f"人设卡应包含 {file_count} 个 TOML 文件"
        )
        self.assertGreater(
            toml_file_count,
            1,
            "TOML 文件数量应大于 1"
        )
        
        # 验证应失败
        is_valid, error_msg = PersonaCardService.validate_toml_file(persona_card)
        self.assertFalse(
            is_valid,
            "包含多个 TOML 文件的人设卡验证应失败"
        )
        self.assertIsNotNone(
            error_msg,
            "验证失败时应返回错误消息"
        )
        self.assertTrue(
            len(error_msg) > 0,
            "错误消息不应为空"
        )
        self.assertIn(
            "只能包含一个",
            error_msg,
            "错误消息应明确指出 TOML 文件过多"
        )
    
    @given(
        name=valid_pc_name,
        description=valid_description,
        toml_content=valid_toml_content
    )
    @settings(max_examples=100, deadline=None)
    def test_property_11_toml_file_must_be_named_bot_config(
        self,
        name,
        description,
        toml_content
    ):
        """属性 11：TOML 文件必须命名为 bot_config.toml
        
        **Validates: Requirements 2.12**
        
        对于任意人设卡，只有 original_name 为 'bot_config.toml' 的文件
        才会被识别为有效的 TOML 配置文件。
        """
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        
        # 创建人设卡
        persona_card = PersonaCardService.create_persona_card(user, {
            'name': name,
            'description': description
        })
        
        # 创建一个名称不正确的 TOML 文件
        toml_file_path = os.path.join(self.temp_dir, 'config.toml')
        with open(toml_file_path, 'w', encoding='utf-8') as f:
            f.write(toml_content)
        
        # 创建文件记录（original_name 不是 bot_config.toml）
        PersonaCardFile.objects.create(
            persona_card=persona_card,
            file_name=f'config_{uuid.uuid4().hex[:8]}.toml',
            original_name='config.toml',  # 错误的名称
            file_path=toml_file_path,
            file_type='application/toml',
            file_size=len(toml_content)
        )
        
        # 验证应失败（因为没有名为 bot_config.toml 的文件）
        is_valid, error_msg = PersonaCardService.validate_toml_file(persona_card)
        self.assertFalse(
            is_valid,
            "不包含 bot_config.toml 文件的人设卡验证应失败"
        )
        self.assertIn(
            "必须包含",
            error_msg,
            "错误消息应提示缺少 bot_config.toml 文件"
        )
        
        # 验证 bot_config.toml 文件数量为 0
        toml_file_count = persona_card.files.filter(
            original_name='bot_config.toml'
        ).count()
        self.assertEqual(
            toml_file_count,
            0,
            "应该没有名为 bot_config.toml 的文件"
        )

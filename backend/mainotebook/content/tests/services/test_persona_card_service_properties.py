"""人设卡服务属性测试

使用 Hypothesis 进行基于属性的测试，验证人设卡服务的权限验证逻辑。

测试属性：
- 属性 1: 用户权限验证
- 属性 41: 私有人设卡编辑权限
- 属性 42: 审核中或已通过人设卡编辑限制
- 属性 48: 下载权限验证

验证需求：1.1, 12.3, 12.4, 13.1
"""

from django.contrib.auth.models import AnonymousUser
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase
from mainotebook.system.models import Users
from mainotebook.content.models import PersonaCard
from mainotebook.content.services.persona_card_service import PersonaCardService


class PersonaCardServicePropertiesTest(HypothesisTestCase):
    """人设卡服务属性测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建基础测试用户
        self.base_user = Users.objects.create(
            username="base_user",
            name="基础用户",
            email="base@example.com",
            is_active=True
        )
    
    def tearDown(self):
        """测试后清理"""
        PersonaCard.objects.all().delete()
        Users.objects.all().delete()
    
    # ========== 属性 1: 用户权限验证 ==========
    
    @settings(max_examples=100, deadline=None)
    @given(
        is_active=st.booleans(),
        is_banned=st.booleans(),
        is_muted=st.booleans()
    )
    def test_property_1_user_permission_validation(
        self,
        is_active: bool,
        is_banned: bool,
        is_muted: bool
    ):
        """
        **验证需求：1.1**
        
        Feature: persona-card-upload, Property 1: 用户权限验证
        
        对于任意用户和上传请求，只有已注册且未被封禁的用户才能成功上传人设卡。
        
        测试策略：
        - 生成不同状态的用户（激活/未激活、封禁/未封禁、禁言/未禁言）
        - 验证只有 is_active=True 且 is_banned=False 且 is_muted=False 的用户有上传权限
        """
        # 创建测试用户
        user = Users.objects.create(
            username=f"test_user_{is_active}_{is_banned}_{is_muted}",
            name="测试用户",
            email=f"test_{is_active}_{is_banned}_{is_muted}@example.com",
            is_active=is_active
        )
        
        # 设置封禁和禁言状态（动态添加属性）
        if is_banned:
            user.is_banned = is_banned
        if is_muted:
            user.is_muted = is_muted
        
        # 检查上传权限
        can_upload = PersonaCardService.check_upload_permission(user)
        
        # 验证权限：只有激活且未被封禁且未被禁言的用户才能上传
        expected = is_active and not is_banned and not is_muted
        
        self.assertEqual(
            can_upload,
            expected,
            f"权限验证错误: is_active={is_active}, is_banned={is_banned}, "
            f"is_muted={is_muted}, expected={expected}, actual={can_upload}"
        )
    
    # ========== 属性 41: 私有人设卡编辑权限 ==========
    
    @settings(max_examples=100, deadline=None)
    @given(
        is_owner=st.booleans(),
        is_public=st.booleans(),
        is_pending=st.booleans()
    )
    def test_property_41_private_persona_card_edit_permission(
        self,
        is_owner: bool,
        is_public: bool,
        is_pending: bool
    ):
        """
        **验证需求：12.3**
        
        Feature: persona-card-upload, Property 41: 私有人设卡编辑权限
        
        对于任意 is_public 为 False 且 is_pending 为 False 的人设卡，
        上传者应能编辑其内容。
        
        测试策略：
        - 生成不同状态的人设卡（公开/私有、审核中/未审核）
        - 测试上传者和非上传者的编辑权限
        - 验证只有上传者可以编辑私有且未审核的人设卡
        """
        # 创建另一个用户
        other_user = Users.objects.create(
            username=f"other_user_{is_owner}_{is_public}_{is_pending}",
            name="其他用户",
            email=f"other_{is_owner}_{is_public}_{is_pending}@example.com",
            is_active=True
        )
        
        # 创建人设卡
        persona_card = PersonaCard.objects.create(
            name=f"测试人设卡_{is_owner}_{is_public}_{is_pending}",
            description="测试描述",
            uploader=self.base_user,
            is_public=is_public,
            is_pending=is_pending
        )
        
        # 选择测试用户（上传者或其他用户）
        test_user = self.base_user if is_owner else other_user
        
        # 检查编辑权限
        can_edit = PersonaCardService.check_edit_permission(test_user, persona_card)
        
        # 验证权限：只有上传者可以编辑私有且未审核的人设卡
        # 条件：is_owner=True AND is_public=False AND is_pending=False
        expected = is_owner and not is_public and not is_pending
        
        self.assertEqual(
            can_edit,
            expected,
            f"编辑权限验证错误: is_owner={is_owner}, is_public={is_public}, "
            f"is_pending={is_pending}, expected={expected}, actual={can_edit}"
        )
    
    # ========== 属性 42: 审核中或已通过人设卡编辑限制 ==========
    
    @settings(max_examples=100, deadline=None)
    @given(
        is_public=st.booleans(),
        is_pending=st.booleans()
    )
    def test_property_42_pending_or_approved_card_edit_restriction(
        self,
        is_public: bool,
        is_pending: bool
    ):
        """
        **验证需求：12.4**
        
        Feature: persona-card-upload, Property 42: 审核中或已通过人设卡编辑限制
        
        对于任意 is_pending 为 True 或（is_public 为 True 且 is_pending 为 False）的人设卡，
        系统应禁止上传者编辑。
        
        测试策略：
        - 生成不同状态的人设卡
        - 验证上传者对审核中或已通过审核的公开人设卡没有编辑权限
        """
        # 创建人设卡
        persona_card = PersonaCard.objects.create(
            name=f"测试人设卡_{is_public}_{is_pending}",
            description="测试描述",
            uploader=self.base_user,
            is_public=is_public,
            is_pending=is_pending
        )
        
        # 检查编辑权限（上传者）
        can_edit = PersonaCardService.check_edit_permission(self.base_user, persona_card)
        
        # 验证权限：审核中或已通过审核的公开人设卡不能编辑
        # 不能编辑的条件：is_pending=True OR (is_public=True AND is_pending=False)
        # 能编辑的条件：is_pending=False AND is_public=False
        should_be_editable = not is_pending and not is_public
        
        self.assertEqual(
            can_edit,
            should_be_editable,
            f"编辑限制验证错误: is_public={is_public}, is_pending={is_pending}, "
            f"should_be_editable={should_be_editable}, actual={can_edit}"
        )
        
        # 特别验证：审核中的人设卡（is_pending=True）不能编辑
        if is_pending:
            self.assertFalse(
                can_edit,
                f"审核中的人设卡不应该可以编辑: is_pending={is_pending}, can_edit={can_edit}"
            )
        
        # 特别验证：已通过审核的公开人设卡（is_public=True AND is_pending=False）不能编辑
        if is_public and not is_pending:
            self.assertFalse(
                can_edit,
                f"已通过审核的公开人设卡不应该可以编辑: is_public={is_public}, "
                f"is_pending={is_pending}, can_edit={can_edit}"
            )
    
    # ========== 属性 48: 下载权限验证 ==========
    
    @settings(max_examples=100, deadline=None)
    @given(
        is_authenticated=st.booleans(),
        is_public=st.booleans(),
        is_pending=st.booleans()
    )
    def test_property_48_download_permission_validation(
        self,
        is_authenticated: bool,
        is_public: bool,
        is_pending: bool
    ):
        """
        **验证需求：13.1**
        
        Feature: persona-card-upload, Property 48: 下载权限验证
        
        对于任意下载请求，只有已注册用户才能下载 is_public 为 True 且 is_pending 为 False 的人设卡。
        
        测试策略：
        - 生成不同状态的人设卡（公开/私有、审核中/已审核）
        - 测试已认证用户和未认证用户的下载权限
        - 验证只有已认证用户可以下载公开且已通过审核的人设卡
        """
        # 创建人设卡
        persona_card = PersonaCard.objects.create(
            name=f"测试人设卡_{is_authenticated}_{is_public}_{is_pending}",
            description="测试描述",
            uploader=self.base_user,
            is_public=is_public,
            is_pending=is_pending
        )
        
        # 选择测试用户（已认证或未认证）
        if is_authenticated:
            test_user = Users.objects.create(
                username=f"download_user_{is_authenticated}_{is_public}_{is_pending}",
                name="下载用户",
                email=f"download_{is_authenticated}_{is_public}_{is_pending}@example.com",
                is_active=True
            )
        else:
            test_user = AnonymousUser()
        
        # 检查下载权限
        can_download = PersonaCardService.check_download_permission(test_user, persona_card)
        
        # 验证权限：只有已认证用户可以下载公开且已通过审核的人设卡
        # 条件：is_authenticated=True AND is_public=True AND is_pending=False
        expected = is_authenticated and is_public and not is_pending
        
        self.assertEqual(
            can_download,
            expected,
            f"下载权限验证错误: is_authenticated={is_authenticated}, is_public={is_public}, "
            f"is_pending={is_pending}, expected={expected}, actual={can_download}"
        )
        
        # 特别验证：未认证用户不能下载任何人设卡
        if not is_authenticated:
            self.assertFalse(
                can_download,
                f"未认证用户不应该可以下载: is_authenticated={is_authenticated}, "
                f"can_download={can_download}"
            )
        
        # 特别验证：私有人设卡不能下载
        if not is_public:
            self.assertFalse(
                can_download,
                f"私有人设卡不应该可以下载: is_public={is_public}, can_download={can_download}"
            )
        
        # 特别验证：审核中的人设卡不能下载
        if is_pending:
            self.assertFalse(
                can_download,
                f"审核中的人设卡不应该可以下载: is_pending={is_pending}, can_download={can_download}"
            )

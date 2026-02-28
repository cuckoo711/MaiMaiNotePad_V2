"""审核属性测试模块

使用 Hypothesis 进行基于属性的测试，验证审核系统的核心属性。

**Validates: Requirements 3.1, 3.2, 3.3**
"""

import uuid
from django.core.exceptions import ValidationError
from hypothesis import given, settings, strategies as st, assume
from hypothesis.extra.django import TestCase

from mainotebook.system.models import Users
from mainotebook.content.models import KnowledgeBase, PersonaCard, UploadRecord
from mainotebook.content.services.review_service import ReviewService


# 配置 Hypothesis
settings.register_profile("default", max_examples=100, deadline=None)
settings.load_profile("default")


# 自定义策略：生成有效的内容名称
valid_content_name = st.text(
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

# 自定义策略：生成内容类型
content_type_strategy = st.sampled_from(['knowledge', 'persona'])

# 自定义策略：生成拒绝原因
rejection_reason_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'P', 'Z'),
    ),
    min_size=1,
    max_size=500
).filter(lambda x: x.strip() != '')


class ReviewPendingListPropertyTest(TestCase):
    """审核待审核列表属性测试
    
    **属性 13：待审核列表仅包含待审核内容**
    **Validates: Requirements 3.1**
    
    验证待审核列表的过滤规则：
    - 待审核列表应仅包含 is_pending=True 的内容
    - 待审核列表不应包含 is_deleted=True 的内容
    - 待审核列表应包含知识库和人设卡两种类型
    - 已审核通过或已拒绝的内容不应出现在待审核列表中
    """
    
    @given(
        name=valid_content_name,
        description=valid_description,
        content_type=content_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_13_pending_list_only_contains_pending_content(
        self, name, description, content_type
    ):
        """属性 13：待审核列表仅包含待审核内容
        
        **Validates: Requirements 3.1**
        
        对于任意待审核列表查询，返回的所有内容都应该满足
        is_pending=True 且 is_deleted=False。
        """
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        
        # 根据内容类型创建待审核内容
        if content_type == 'knowledge':
            # 创建待审核的知识库
            pending_content = KnowledgeBase.objects.create(
                name=f'{name}_pending',
                description=description,
                uploader=user,
                is_pending=True,
                is_public=False
            )
            
            # 创建已审核通过的知识库
            approved_content = KnowledgeBase.objects.create(
                name=f'{name}_approved',
                description=description,
                uploader=user,
                is_pending=False,
                is_public=True
            )
            
            # 创建已拒绝的知识库
            rejected_content = KnowledgeBase.objects.create(
                name=f'{name}_rejected',
                description=description,
                uploader=user,
                is_pending=False,
                is_public=False,
                rejection_reason='测试拒绝原因'
            )
        else:  # persona
            # 创建待审核的人设卡
            pending_content = PersonaCard.objects.create(
                name=f'{name}_pending',
                description=description,
                uploader=user,
                is_pending=True,
                is_public=False
            )
            
            # 创建已审核通过的人设卡
            approved_content = PersonaCard.objects.create(
                name=f'{name}_approved',
                description=description,
                uploader=user,
                is_pending=False,
                is_public=True
            )
            
            # 创建已拒绝的人设卡
            rejected_content = PersonaCard.objects.create(
                name=f'{name}_rejected',
                description=description,
                uploader=user,
                is_pending=False,
                is_public=False,
                rejection_reason='测试拒绝原因'
            )
        
        # 获取待审核列表（返回 dict，包含 items 和 total）
        result = ReviewService.get_pending_items(page_size=9999)
        pending_items = result['items']
        pending_ids = [item['id'] for item in pending_items]
        
        # 断言：待审核内容应在列表中
        self.assertIn(
            pending_content.id,
            pending_ids,
            f"待审核的{content_type}应出现在待审核列表中"
        )
        
        # 断言：已审核通过的内容不应在列表中
        self.assertNotIn(
            approved_content.id,
            pending_ids,
            f"已审核通过的{content_type}不应出现在待审核列表中"
        )
        
        # 断言：已拒绝的内容不应在列表中
        self.assertNotIn(
            rejected_content.id,
            pending_ids,
            f"已拒绝的{content_type}不应出现在待审核列表中"
        )
        
        # 断言：列表中所有内容都应满足 is_pending=True
        for item in pending_items:
            if item['content_type'] == 'knowledge':
                content = KnowledgeBase.objects.get(id=item['id'])
            else:
                content = PersonaCard.objects.get(id=item['id'])
            
            self.assertTrue(
                content.is_pending,
                f"待审核列表中的内容应满足 is_pending=True: {item['name']}"
            )
    
    @given(
        name=valid_content_name,
        description=valid_description
    )
    @settings(max_examples=100, deadline=None)
    def test_property_13_pending_list_excludes_deleted_content(
        self, name, description
    ):
        """属性 13：待审核列表不包含已删除内容
        
        **Validates: Requirements 3.1**
        
        对于任意已删除的内容，即使其状态为待审核，
        也不应出现在待审核列表中。
        """
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        
        # 创建待审核的知识库
        kb = KnowledgeBase.objects.create(
            name=name,
            description=description,
            uploader=user,
            is_pending=True,
            is_public=False
        )
        
        # 验证知识库在待审核列表中（返回 dict，包含 items 和 total）
        result_before = ReviewService.get_pending_items(page_size=9999)
        pending_ids_before = [item['id'] for item in result_before['items']]
        self.assertIn(kb.id, pending_ids_before, "删除前应在待审核列表中")
        
        # 软删除知识库（如果模型支持）
        if hasattr(kb, 'is_deleted'):
            kb.is_deleted = True
            kb.save()
            
            # 获取待审核列表（返回 dict，包含 items 和 total）
            result_after = ReviewService.get_pending_items(page_size=9999)
            pending_ids_after = [item['id'] for item in result_after['items']]
            
            # 断言：已删除的知识库不应在待审核列表中
            self.assertNotIn(
                kb.id,
                pending_ids_after,
                "已删除的内容不应出现在待审核列表中"
            )
        else:
            # 如果模型不支持软删除，跳过此测试
            self.skipTest("模型不支持 is_deleted 字段，无法测试软删除过滤")
    
    @given(
        kb_name=valid_content_name,
        pc_name=valid_content_name,
        description=valid_description
    )
    @settings(max_examples=100, deadline=None)
    def test_property_13_pending_list_includes_both_content_types(
        self, kb_name, pc_name, description
    ):
        """属性 13：待审核列表包含两种内容类型
        
        **Validates: Requirements 3.1**
        
        待审核列表应同时包含知识库和人设卡两种类型的内容。
        """
        # 跳过相同名称的情况
        assume(kb_name != pc_name)
        
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        
        # 创建待审核的知识库
        kb = KnowledgeBase.objects.create(
            name=kb_name,
            description=description,
            uploader=user,
            is_pending=True,
            is_public=False
        )
        
        # 创建待审核的人设卡
        pc = PersonaCard.objects.create(
            name=pc_name,
            description=description,
            uploader=user,
            is_pending=True,
            is_public=False
        )
        
        # 获取待审核列表（返回 dict，包含 items 和 total）
        result = ReviewService.get_pending_items(page_size=9999)
        pending_items = result['items']
        
        # 提取内容类型
        content_types = [item['content_type'] for item in pending_items]
        pending_ids = [item['id'] for item in pending_items]
        
        # 断言：列表应包含知识库
        self.assertIn('knowledge', content_types, "待审核列表应包含知识库类型")
        self.assertIn(kb.id, pending_ids, "待审核列表应包含创建的知识库")
        
        # 断言：列表应包含人设卡
        self.assertIn('persona', content_types, "待审核列表应包含人设卡类型")
        self.assertIn(pc.id, pending_ids, "待审核列表应包含创建的人设卡")


class ReviewApprovePropertyTest(TestCase):
    """审核批准属性测试
    
    **属性 14：批准内容更新状态**
    **Validates: Requirements 3.2**
    
    验证批准内容的状态更新：
    - 批准后 is_public 应为 True
    - 批准后 is_pending 应为 False
    - 批准后 rejection_reason 应为空
    - 上传记录状态应更新为 'approved'
    """
    
    @given(
        name=valid_content_name,
        description=valid_description,
        content_type=content_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_14_approve_content_updates_status(
        self, name, description, content_type
    ):
        """属性 14：批准内容更新状态
        
        **Validates: Requirements 3.2**
        
        对于任意待审核的内容，批准后 is_public 应该为 True，
        is_pending 应该为 False，rejection_reason 应该为空。
        """
        # 创建用户和审核员
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        reviewer = Users.objects.create(
            username=f'reviewer_{uuid.uuid4().hex[:8]}',
            password='test_password',
            is_staff=True
        )
        
        # 根据内容类型创建待审核内容
        if content_type == 'knowledge':
            content = KnowledgeBase.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=True,
                is_public=False,
                rejection_reason='旧的拒绝原因'  # 测试是否会被清空
            )
        else:  # persona
            content = PersonaCard.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=True,
                is_public=False,
                rejection_reason='旧的拒绝原因'  # 测试是否会被清空
            )
        
        # 创建上传记录
        UploadRecord.objects.create(
            uploader=user,
            target_id=str(content.id),
            target_type=content_type,
            name=content.name,
            description=content.description,
            status='pending'
        )
        
        # 验证初始状态
        self.assertTrue(content.is_pending, "批准前应处于待审核状态")
        self.assertFalse(content.is_public, "批准前不应公开")
        
        # 批准内容
        ReviewService.approve_content(str(content.id), content_type, reviewer)
        
        # 刷新对象
        content.refresh_from_db()
        
        # 断言：is_public 应为 True
        self.assertTrue(
            content.is_public,
            f"批准后{content_type}应公开 (is_public=True)"
        )
        
        # 断言：is_pending 应为 False
        self.assertFalse(
            content.is_pending,
            f"批准后{content_type}不应处于待审核状态 (is_pending=False)"
        )
        
        # 断言：rejection_reason 应为空
        self.assertIsNone(
            content.rejection_reason,
            f"批准后{content_type}的拒绝原因应为空"
        )
        
        # 断言：上传记录状态应更新为 'approved'
        upload_record = UploadRecord.objects.get(
            target_id=str(content.id),
            target_type=content_type
        )
        self.assertEqual(
            upload_record.status,
            'approved',
            "批准后上传记录状态应为 'approved'"
        )
    
    @given(
        name=valid_content_name,
        description=valid_description,
        content_type=content_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_14_cannot_approve_non_pending_content(
        self, name, description, content_type
    ):
        """属性 14：不能批准非待审核状态的内容
        
        **Validates: Requirements 3.2**
        
        对于任意非待审核状态的内容，批准操作应失败。
        """
        # 创建用户和审核员
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        reviewer = Users.objects.create(
            username=f'reviewer_{uuid.uuid4().hex[:8]}',
            password='test_password',
            is_staff=True
        )
        
        # 根据内容类型创建已审核通过的内容
        if content_type == 'knowledge':
            content = KnowledgeBase.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=False,  # 已审核
                is_public=True
            )
        else:  # persona
            content = PersonaCard.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=False,  # 已审核
                is_public=True
            )
        
        # 断言：批准非待审核内容应失败
        with self.assertRaises(
            ValidationError,
            msg=f"不应允许批准非待审核状态的{content_type}"
        ):
            ReviewService.approve_content(str(content.id), content_type, reviewer)
        
        # 验证状态未改变
        content.refresh_from_db()
        self.assertFalse(content.is_pending, "状态不应被改变")
        self.assertTrue(content.is_public, "状态不应被改变")


class ReviewRejectPropertyTest(TestCase):
    """审核拒绝属性测试
    
    **属性 15：拒绝内容记录原因**
    **Validates: Requirements 3.3**
    
    验证拒绝内容的状态更新：
    - 拒绝后 is_public 应为 False
    - 拒绝后 is_pending 应为 False
    - 拒绝后 rejection_reason 应包含拒绝原因
    - 上传记录状态应更新为 'rejected'
    - 拒绝时必须提供原因
    """
    
    @given(
        name=valid_content_name,
        description=valid_description,
        content_type=content_type_strategy,
        reason=rejection_reason_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_15_reject_content_records_reason(
        self, name, description, content_type, reason
    ):
        """属性 15：拒绝内容记录原因
        
        **Validates: Requirements 3.3**
        
        对于任意待审核的内容，拒绝后 is_public 应该为 False，
        is_pending 应该为 False，rejection_reason 应该包含拒绝原因。
        """
        # 创建用户和审核员
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        reviewer = Users.objects.create(
            username=f'reviewer_{uuid.uuid4().hex[:8]}',
            password='test_password',
            is_staff=True
        )
        
        # 根据内容类型创建待审核内容
        if content_type == 'knowledge':
            content = KnowledgeBase.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=True,
                is_public=False
            )
        else:  # persona
            content = PersonaCard.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=True,
                is_public=False
            )
        
        # 创建上传记录
        UploadRecord.objects.create(
            uploader=user,
            target_id=str(content.id),
            target_type=content_type,
            name=content.name,
            description=content.description,
            status='pending'
        )
        
        # 验证初始状态
        self.assertTrue(content.is_pending, "拒绝前应处于待审核状态")
        self.assertFalse(content.is_public, "拒绝前不应公开")
        self.assertIsNone(content.rejection_reason, "拒绝前不应有拒绝原因")
        
        # 拒绝内容
        ReviewService.reject_content(str(content.id), content_type, reviewer, reason)
        
        # 刷新对象
        content.refresh_from_db()
        
        # 断言：is_public 应为 False
        self.assertFalse(
            content.is_public,
            f"拒绝后{content_type}不应公开 (is_public=False)"
        )
        
        # 断言：is_pending 应为 False
        self.assertFalse(
            content.is_pending,
            f"拒绝后{content_type}不应处于待审核状态 (is_pending=False)"
        )
        
        # 断言：rejection_reason 应包含拒绝原因
        self.assertIsNotNone(
            content.rejection_reason,
            f"拒绝后{content_type}应有拒绝原因"
        )
        self.assertEqual(
            content.rejection_reason,
            reason,
            f"拒绝后{content_type}的拒绝原因应与提供的原因一致"
        )
        
        # 断言：上传记录状态应更新为 'rejected'
        upload_record = UploadRecord.objects.get(
            target_id=str(content.id),
            target_type=content_type
        )
        self.assertEqual(
            upload_record.status,
            'rejected',
            "拒绝后上传记录状态应为 'rejected'"
        )
    
    @given(
        name=valid_content_name,
        description=valid_description,
        content_type=content_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_15_reject_requires_reason(
        self, name, description, content_type
    ):
        """属性 15：拒绝内容必须提供原因
        
        **Validates: Requirements 3.3**
        
        对于任意待审核的内容，拒绝时必须提供原因，
        否则操作应失败。
        """
        # 创建用户和审核员
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        reviewer = Users.objects.create(
            username=f'reviewer_{uuid.uuid4().hex[:8]}',
            password='test_password',
            is_staff=True
        )
        
        # 根据内容类型创建待审核内容
        if content_type == 'knowledge':
            content = KnowledgeBase.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=True,
                is_public=False
            )
        else:  # persona
            content = PersonaCard.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=True,
                is_public=False
            )
        
        # 断言：不提供原因应失败
        with self.assertRaises(
            ValidationError,
            msg=f"拒绝{content_type}时必须提供原因"
        ):
            ReviewService.reject_content(str(content.id), content_type, reviewer, '')
        
        # 断言：只提供空白字符应失败
        with self.assertRaises(
            ValidationError,
            msg=f"拒绝{content_type}时原因不能只包含空白字符"
        ):
            ReviewService.reject_content(str(content.id), content_type, reviewer, '   ')
        
        # 验证状态未改变
        content.refresh_from_db()
        self.assertTrue(content.is_pending, "状态不应被改变")
        self.assertIsNone(content.rejection_reason, "拒绝原因不应被设置")
    
    @given(
        name=valid_content_name,
        description=valid_description,
        content_type=content_type_strategy,
        reason=rejection_reason_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_15_cannot_reject_non_pending_content(
        self, name, description, content_type, reason
    ):
        """属性 15：不能拒绝非待审核状态的内容
        
        **Validates: Requirements 3.3**
        
        对于任意非待审核状态的内容，拒绝操作应失败。
        """
        # 创建用户和审核员
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        reviewer = Users.objects.create(
            username=f'reviewer_{uuid.uuid4().hex[:8]}',
            password='test_password',
            is_staff=True
        )
        
        # 根据内容类型创建已审核通过的内容
        if content_type == 'knowledge':
            content = KnowledgeBase.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=False,  # 已审核
                is_public=True
            )
        else:  # persona
            content = PersonaCard.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=False,  # 已审核
                is_public=True
            )
        
        # 断言：拒绝非待审核内容应失败
        with self.assertRaises(
            ValidationError,
            msg=f"不应允许拒绝非待审核状态的{content_type}"
        ):
            ReviewService.reject_content(
                str(content.id), content_type, reviewer, reason
            )
        
        # 验证状态未改变
        content.refresh_from_db()
        self.assertFalse(content.is_pending, "状态不应被改变")
        self.assertTrue(content.is_public, "状态不应被改变")
        self.assertIsNone(content.rejection_reason, "拒绝原因不应被设置")


# ============================================================
# 分页参数策略
# ============================================================
valid_page = st.integers(min_value=1, max_value=10)
valid_page_size = st.integers(min_value=1, max_value=50)

# 搜索关键词策略：生成简短的字母数字关键词
search_keyword_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
    min_size=1,
    max_size=10
).filter(lambda x: x.strip() != '')


class ReviewPaginationPropertyTest(TestCase):
    """分页响应结构完整性属性测试

    **属性 1：分页响应结构完整性**
    **Validates: Requirements 1.1, 1.2, 1.7**

    验证分页响应的结构和数据完整性：
    - 返回的 items 数量 <= page_size
    - 响应包含 total、items 字段
    - total 等于所有待审核内容的实际总数
    """

    @given(
        page=valid_page,
        page_size=valid_page_size,
        name=valid_content_name,
        description=valid_description,
    )
    @settings(max_examples=100, deadline=None)
    def test_property_1_pagination_response_structure(
        self, page, page_size, name, description
    ):
        """属性 1：分页响应结构完整性

        **Validates: Requirements 1.1, 1.2, 1.7**

        对于任意有效分页参数，返回的 items 数量 <= page_size，
        响应包含 total/items 字段，total 等于实际待审核总数。
        """
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )

        # 创建待审核的知识库和人设卡
        KnowledgeBase.objects.create(
            name=f'{name}_kb',
            description=description,
            uploader=user,
            is_pending=True,
            is_public=False
        )
        PersonaCard.objects.create(
            name=f'{name}_pc',
            description=description,
            uploader=user,
            is_pending=True,
            is_public=False
        )

        # 调用分页查询
        result = ReviewService.get_pending_items(page=page, page_size=page_size)

        # 断言：响应包含 items 和 total 字段
        self.assertIn('items', result, "响应应包含 items 字段")
        self.assertIn('total', result, "响应应包含 total 字段")

        # 断言：items 数量 <= page_size
        self.assertLessEqual(
            len(result['items']),
            page_size,
            f"返回的 items 数量 ({len(result['items'])}) 不应超过 page_size ({page_size})"
        )

        # 断言：total 等于实际待审核总数
        actual_pending_kb = KnowledgeBase.objects.filter(is_pending=True).count()
        actual_pending_pc = PersonaCard.objects.filter(is_pending=True).count()
        actual_total = actual_pending_kb + actual_pending_pc
        self.assertEqual(
            result['total'],
            actual_total,
            f"total ({result['total']}) 应等于实际待审核总数 ({actual_total})"
        )

        # 断言：每条 item 包含必要字段
        required_fields = [
            'id', 'name', 'description', 'content_type',
            'uploader_id', 'uploader_name', 'create_datetime',
            'tags', 'file_count'
        ]
        for item in result['items']:
            for field in required_fields:
                self.assertIn(
                    field, item,
                    f"每条 item 应包含 {field} 字段"
                )


class ReviewOrderingPropertyTest(TestCase):
    """待审核列表排序属性测试

    **属性 2：待审核列表按创建时间倒序排列**
    **Validates: Requirements 1.6**

    验证返回列表中相邻两条记录的 create_datetime 前一条 >= 后一条。
    """

    @given(
        name=valid_content_name,
        description=valid_description,
    )
    @settings(max_examples=100, deadline=None)
    def test_property_2_pending_list_ordered_by_create_datetime_desc(
        self, name, description
    ):
        """属性 2：待审核列表按创建时间倒序排列

        **Validates: Requirements 1.6**

        对于任意一组待审核内容，返回列表中相邻两条记录的
        create_datetime 前一条 >= 后一条。
        """
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )

        # 创建多条待审核内容以确保有排序数据
        KnowledgeBase.objects.create(
            name=f'{name}_kb1',
            description=description,
            uploader=user,
            is_pending=True,
            is_public=False
        )
        PersonaCard.objects.create(
            name=f'{name}_pc1',
            description=description,
            uploader=user,
            is_pending=True,
            is_public=False
        )
        KnowledgeBase.objects.create(
            name=f'{name}_kb2',
            description=description,
            uploader=user,
            is_pending=True,
            is_public=False
        )

        # 获取待审核列表（使用较大的 page_size 获取所有数据）
        result = ReviewService.get_pending_items(page=1, page_size=9999)
        items = result['items']

        # 断言：相邻两条记录的 create_datetime 前一条 >= 后一条
        for i in range(len(items) - 1):
            self.assertGreaterEqual(
                items[i]['create_datetime'],
                items[i + 1]['create_datetime'],
                f"第 {i} 条记录的 create_datetime ({items[i]['create_datetime']}) "
                f"应 >= 第 {i+1} 条记录的 create_datetime ({items[i+1]['create_datetime']})"
            )


class ReviewContentTypeFilterPropertyTest(TestCase):
    """content_type 过滤正确性属性测试

    **属性 3：content_type 过滤正确性**
    **Validates: Requirements 1.4**

    验证指定 content_type 过滤后，返回结果中所有项的
    content_type 等于指定值。
    """

    @given(
        name=valid_content_name,
        description=valid_description,
        filter_type=content_type_strategy,
    )
    @settings(max_examples=100, deadline=None)
    def test_property_3_content_type_filter_correctness(
        self, name, description, filter_type
    ):
        """属性 3：content_type 过滤正确性

        **Validates: Requirements 1.4**

        对于任意一组混合类型的待审核内容，当指定 content_type 过滤参数时，
        返回结果中所有项的 content_type 应等于指定的过滤值。
        """
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )

        # 创建两种类型的待审核内容
        KnowledgeBase.objects.create(
            name=f'{name}_kb',
            description=description,
            uploader=user,
            is_pending=True,
            is_public=False
        )
        PersonaCard.objects.create(
            name=f'{name}_pc',
            description=description,
            uploader=user,
            is_pending=True,
            is_public=False
        )

        # 使用 content_type 过滤查询
        result = ReviewService.get_pending_items(
            filters={'content_type': filter_type},
            page=1,
            page_size=9999
        )
        items = result['items']

        # 断言：所有返回项的 content_type 等于指定的过滤值
        for item in items:
            self.assertEqual(
                item['content_type'],
                filter_type,
                f"过滤 content_type={filter_type} 后，"
                f"返回项的 content_type 应为 {filter_type}，"
                f"但实际为 {item['content_type']}"
            )


class ReviewSearchPropertyTest(TestCase):
    """search 模糊匹配正确性属性测试

    **属性 4：search 模糊匹配正确性**
    **Validates: Requirements 1.5**

    验证返回结果中每条记录的 name 或 description 包含搜索关键词。
    """

    @given(
        keyword=search_keyword_strategy,
        extra_name=valid_content_name,
        description=valid_description,
    )
    @settings(max_examples=100, deadline=None)
    def test_property_4_search_filter_correctness(
        self, keyword, extra_name, description
    ):
        """属性 4：search 模糊匹配正确性

        **Validates: Requirements 1.5**

        对于任意搜索关键词和一组待审核内容，返回结果中每条记录的
        name 或 description 应包含该关键词（不区分大小写）。
        """
        # 创建用户
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )

        # 创建包含关键词的待审核内容
        KnowledgeBase.objects.create(
            name=f'match_{keyword}_kb',
            description=description,
            uploader=user,
            is_pending=True,
            is_public=False
        )

        # 创建描述中包含关键词的待审核内容
        PersonaCard.objects.create(
            name=extra_name,
            description=f'desc_{keyword}_content',
            uploader=user,
            is_pending=True,
            is_public=False
        )

        # 使用 search 过滤查询
        result = ReviewService.get_pending_items(
            filters={'search': keyword},
            page=1,
            page_size=9999
        )
        items = result['items']

        # 断言：每条返回记录的 name 或 description 包含搜索关键词（不区分大小写）
        keyword_lower = keyword.lower()
        for item in items:
            name_match = keyword_lower in (item['name'] or '').lower()
            desc_match = keyword_lower in (item['description'] or '').lower()
            self.assertTrue(
                name_match or desc_match,
                f"搜索关键词 '{keyword}' 应出现在 name ('{item['name']}') "
                f"或 description ('{item['description']}') 中"
            )


class ReviewApproveFullStatePropertyTest(TestCase):
    """审核通过完整状态变更属性测试

    **属性 5：审核通过完整状态变更**
    **Validates: Requirements 2.1, 2.2**

    验证 approve 操作后的完整状态变更：
    - is_pending=False
    - is_public=True
    - rejection_reason=null
    - UploadRecord.status='approved'

    注意：此属性与属性 14 有重叠，但属性 5 更聚焦于需求 2.1 和 2.2 的完整验证。
    """

    @given(
        name=valid_content_name,
        description=valid_description,
        content_type=content_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_5_approve_full_state_change(
        self, name, description, content_type
    ):
        """属性 5：审核通过完整状态变更

        **Validates: Requirements 2.1, 2.2**

        对于任意待审核内容，执行 approve 操作后：
        is_pending=False, is_public=True, rejection_reason=null,
        UploadRecord.status='approved'。
        """
        # 创建用户和审核员
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        reviewer = Users.objects.create(
            username=f'reviewer_{uuid.uuid4().hex[:8]}',
            password='test_password',
            is_staff=True
        )

        # 根据内容类型创建待审核内容（带旧的拒绝原因，验证会被清空）
        if content_type == 'knowledge':
            content = KnowledgeBase.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=True,
                is_public=False,
                rejection_reason='旧的拒绝原因'
            )
        else:
            content = PersonaCard.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=True,
                is_public=False,
                rejection_reason='旧的拒绝原因'
            )

        # 创建上传记录
        UploadRecord.objects.create(
            uploader=user,
            target_id=str(content.id),
            target_type=content_type,
            name=content.name,
            description=content.description,
            status='pending'
        )

        # 执行审核通过
        ReviewService.approve_content(str(content.id), content_type, reviewer)

        # 刷新对象
        content.refresh_from_db()

        # 验证完整状态变更
        self.assertFalse(content.is_pending, "审核通过后 is_pending 应为 False")
        self.assertTrue(content.is_public, "审核通过后 is_public 应为 True")
        self.assertIsNone(content.rejection_reason, "审核通过后 rejection_reason 应为 null")

        # 验证 UploadRecord 状态
        upload_record = UploadRecord.objects.get(
            target_id=str(content.id),
            target_type=content_type
        )
        self.assertEqual(
            upload_record.status, 'approved',
            "审核通过后 UploadRecord.status 应为 'approved'"
        )


class ReviewRejectFullStatePropertyTest(TestCase):
    """审核拒绝完整状态变更属性测试

    **属性 6：审核拒绝完整状态变更**
    **Validates: Requirements 3.1, 3.2**

    验证 reject 操作后的完整状态变更：
    - is_pending=False
    - is_public=False
    - rejection_reason=reason
    - UploadRecord.status='rejected'

    注意：此属性与属性 15 有重叠，但属性 6 更聚焦于需求 3.1 和 3.2 的完整验证。
    """

    @given(
        name=valid_content_name,
        description=valid_description,
        content_type=content_type_strategy,
        reason=rejection_reason_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_6_reject_full_state_change(
        self, name, description, content_type, reason
    ):
        """属性 6：审核拒绝完整状态变更

        **Validates: Requirements 3.1, 3.2**

        对于任意待审核内容和有效拒绝原因，执行 reject 操作后：
        is_pending=False, is_public=False, rejection_reason=reason,
        UploadRecord.status='rejected'。
        """
        # 创建用户和审核员
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        reviewer = Users.objects.create(
            username=f'reviewer_{uuid.uuid4().hex[:8]}',
            password='test_password',
            is_staff=True
        )

        # 根据内容类型创建待审核内容
        if content_type == 'knowledge':
            content = KnowledgeBase.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=True,
                is_public=False
            )
        else:
            content = PersonaCard.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=True,
                is_public=False
            )

        # 创建上传记录
        UploadRecord.objects.create(
            uploader=user,
            target_id=str(content.id),
            target_type=content_type,
            name=content.name,
            description=content.description,
            status='pending'
        )

        # 执行审核拒绝
        ReviewService.reject_content(str(content.id), content_type, reviewer, reason)

        # 刷新对象
        content.refresh_from_db()

        # 验证完整状态变更
        self.assertFalse(content.is_pending, "审核拒绝后 is_pending 应为 False")
        self.assertFalse(content.is_public, "审核拒绝后 is_public 应为 False")
        self.assertEqual(
            content.rejection_reason, reason,
            "审核拒绝后 rejection_reason 应等于提供的原因"
        )

        # 验证 UploadRecord 状态
        upload_record = UploadRecord.objects.get(
            target_id=str(content.id),
            target_type=content_type
        )
        self.assertEqual(
            upload_record.status, 'rejected',
            "审核拒绝后 UploadRecord.status 应为 'rejected'"
        )


class ReviewReasonValidationPropertyTest(TestCase):
    """拒绝操作 reason 校验属性测试

    **属性 7：拒绝操作 reason 校验**
    **Validates: Requirements 3.3, 3.4**

    验证拒绝操作的 reason 校验规则：
    - 空白 reason 抛出 ValidationError
    - 超过 500 字符的 reason 抛出 ValidationError
    """

    @given(
        name=valid_content_name,
        description=valid_description,
        content_type=content_type_strategy,
        blank_reason=st.text(
            alphabet=st.sampled_from(' \t\n\r'),
            min_size=0,
            max_size=20
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_7_blank_reason_raises_validation_error(
        self, name, description, content_type, blank_reason
    ):
        """属性 7：空白 reason 抛出 ValidationError

        **Validates: Requirements 3.3**

        对于任意空白字符串（空字符串或纯空白字符）作为 reason，
        reject 操作应抛出 ValidationError。
        """
        # 创建用户和审核员
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        reviewer = Users.objects.create(
            username=f'reviewer_{uuid.uuid4().hex[:8]}',
            password='test_password',
            is_staff=True
        )

        # 根据内容类型创建待审核内容
        if content_type == 'knowledge':
            content = KnowledgeBase.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=True,
                is_public=False
            )
        else:
            content = PersonaCard.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=True,
                is_public=False
            )

        # 断言：空白 reason 应抛出 ValidationError
        with self.assertRaises(ValidationError):
            ReviewService.reject_content(
                str(content.id), content_type, reviewer, blank_reason
            )

        # 验证状态未改变
        content.refresh_from_db()
        self.assertTrue(content.is_pending, "空白 reason 不应改变内容状态")

    @given(
        name=valid_content_name,
        description=valid_description,
        content_type=content_type_strategy,
        long_reason=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd'),
            ),
            min_size=501,
            max_size=1000
        ).filter(lambda x: x.strip() != '')
    )
    @settings(max_examples=100, deadline=None)
    def test_property_7_long_reason_raises_validation_error(
        self, name, description, content_type, long_reason
    ):
        """属性 7：超过 500 字符的 reason 抛出 ValidationError

        **Validates: Requirements 3.4**

        对于任意长度超过 500 字符的字符串作为 reason，
        reject 操作应抛出 ValidationError。
        """
        # 创建用户和审核员
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        reviewer = Users.objects.create(
            username=f'reviewer_{uuid.uuid4().hex[:8]}',
            password='test_password',
            is_staff=True
        )

        # 根据内容类型创建待审核内容
        if content_type == 'knowledge':
            content = KnowledgeBase.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=True,
                is_public=False
            )
        else:
            content = PersonaCard.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=True,
                is_public=False
            )

        # 断言：超长 reason 应抛出 ValidationError
        with self.assertRaises(ValidationError):
            ReviewService.reject_content(
                str(content.id), content_type, reviewer, long_reason
            )

        # 验证状态未改变
        content.refresh_from_db()
        self.assertTrue(content.is_pending, "超长 reason 不应改变内容状态")


class ReviewNonPendingOperationPropertyTest(TestCase):
    """非待审核内容拒绝审核操作属性测试

    **属性 8：非待审核内容拒绝审核操作**
    **Validates: Requirements 2.6, 3.7, 4.4**

    验证 is_pending=False 的内容执行 approve/reject/return_draft 时
    均抛出 ValidationError。
    """

    @given(
        name=valid_content_name,
        description=valid_description,
        content_type=content_type_strategy,
        reason=rejection_reason_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_8_non_pending_content_rejects_all_operations(
        self, name, description, content_type, reason
    ):
        """属性 8：非待审核内容拒绝所有审核操作

        **Validates: Requirements 2.6, 3.7, 4.4**

        对于任意 is_pending=False 的内容，执行 approve、reject、
        return_draft 操作时均应抛出 ValidationError。
        """
        # 创建用户和审核员
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        reviewer = Users.objects.create(
            username=f'reviewer_{uuid.uuid4().hex[:8]}',
            password='test_password',
            is_staff=True
        )

        # 根据内容类型创建非待审核内容（已通过）
        if content_type == 'knowledge':
            content = KnowledgeBase.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=False,
                is_public=True
            )
        else:
            content = PersonaCard.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=False,
                is_public=True
            )

        content_id = str(content.id)

        # 断言：approve 操作应抛出 ValidationError
        with self.assertRaises(
            ValidationError,
            msg="非待审核内容执行 approve 应抛出 ValidationError"
        ):
            ReviewService.approve_content(content_id, content_type, reviewer)

        # 断言：reject 操作应抛出 ValidationError
        with self.assertRaises(
            ValidationError,
            msg="非待审核内容执行 reject 应抛出 ValidationError"
        ):
            ReviewService.reject_content(content_id, content_type, reviewer, reason)

        # 断言：return_draft 操作应抛出 ValidationError
        with self.assertRaises(
            ValidationError,
            msg="非待审核内容执行 return_draft 应抛出 ValidationError"
        ):
            ReviewService.return_content(content_id, content_type, reviewer, reason)

        # 验证状态未改变
        content.refresh_from_db()
        self.assertFalse(content.is_pending, "状态不应被改变")
        self.assertTrue(content.is_public, "公开状态不应被改变")


class ReviewInvalidContentTypePropertyTest(TestCase):
    """无效 content_type 拒绝属性测试

    **属性 9：无效 content_type 拒绝**
    **Validates: Requirements 2.4**

    验证非 knowledge/persona 的 content_type 调用
    approve_content/reject_content 时抛出 ValidationError。
    """

    @given(
        invalid_type=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
            min_size=1,
            max_size=50
        ).filter(lambda x: x.strip() != '' and x not in ('knowledge', 'persona')),
        reason=rejection_reason_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_9_invalid_content_type_raises_error(
        self, invalid_type, reason
    ):
        """属性 9：无效 content_type 抛出 ValidationError

        **Validates: Requirements 2.4**

        对于任意不是 'knowledge' 或 'persona' 的字符串作为 content_type，
        approve_content 和 reject_content 均应抛出 ValidationError。
        """
        # 创建审核员
        reviewer = Users.objects.create(
            username=f'reviewer_{uuid.uuid4().hex[:8]}',
            password='test_password',
            is_staff=True
        )

        # 使用随机 UUID 作为 content_id
        fake_id = str(uuid.uuid4())

        # 断言：approve_content 应抛出 ValidationError
        with self.assertRaises(
            ValidationError,
            msg=f"无效 content_type '{invalid_type}' 调用 approve_content 应抛出 ValidationError"
        ):
            ReviewService.approve_content(fake_id, invalid_type, reviewer)

        # 断言：reject_content 应抛出 ValidationError
        with self.assertRaises(
            ValidationError,
            msg=f"无效 content_type '{invalid_type}' 调用 reject_content 应抛出 ValidationError"
        ):
            ReviewService.reject_content(fake_id, invalid_type, reviewer, reason)


class ReviewReturnDraftPropertyTest(TestCase):
    """退回操作状态变更属性测试

    **属性 10：退回操作状态变更**
    **Validates: Requirements 4.1**

    验证 return_draft 操作后的完整状态变更：
    - is_pending=False
    - is_public=False
    - 退回原因已保存
    - UploadRecord.status='rejected'
    """

    @given(
        name=valid_content_name,
        description=valid_description,
        content_type=content_type_strategy,
        reason=rejection_reason_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_10_return_draft_state_change(
        self, name, description, content_type, reason
    ):
        """属性 10：退回操作状态变更

        **Validates: Requirements 4.1**

        对于任意待审核内容，执行 return_draft 操作后：
        is_pending=False, is_public=False, 退回原因已保存,
        UploadRecord.status='rejected'。
        """
        # 创建用户和审核员
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        reviewer = Users.objects.create(
            username=f'reviewer_{uuid.uuid4().hex[:8]}',
            password='test_password',
            is_staff=True
        )

        # 根据内容类型创建待审核内容
        if content_type == 'knowledge':
            content = KnowledgeBase.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=True,
                is_public=False
            )
        else:
            content = PersonaCard.objects.create(
                name=name,
                description=description,
                uploader=user,
                is_pending=True,
                is_public=False
            )

        # 创建上传记录
        UploadRecord.objects.create(
            uploader=user,
            target_id=str(content.id),
            target_type=content_type,
            name=content.name,
            description=content.description,
            status='pending'
        )

        # 执行退回操作
        ReviewService.return_content(str(content.id), content_type, reviewer, reason)

        # 刷新对象
        content.refresh_from_db()

        # 验证状态变更
        self.assertFalse(content.is_pending, "退回后 is_pending 应为 False")
        self.assertFalse(content.is_public, "退回后 is_public 应为 False")
        self.assertEqual(
            content.rejection_reason, reason,
            "退回后退回原因应已保存"
        )

        # 验证 UploadRecord 状态（任务 2.9 添加的功能）
        upload_record = UploadRecord.objects.get(
            target_id=str(content.id),
            target_type=content_type
        )
        self.assertEqual(
            upload_record.status, 'rejected',
            "退回后 UploadRecord.status 应为 'rejected'"
        )


class ReviewBatchApprovePropertyTest(TestCase):
    """批量审核通过状态变更属性测试

    **属性 11：批量审核通过状态变更**
    **Validates: Requirements 6.1**

    验证 batch_approve 后所有成功项满足：
    - is_pending=False
    - is_public=True
    - rejection_reason=null
    """

    @given(
        name=valid_content_name,
        description=valid_description,
        content_type=content_type_strategy,
        count=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_11_batch_approve_state_change(
        self, name, description, content_type, count
    ):
        """属性 11：批量审核通过状态变更

        **Validates: Requirements 6.1**

        对于任意一组待审核内容 ID，执行 batch_approve 后，
        所有成功处理的内容应满足 is_pending=False、is_public=True、
        rejection_reason=null。
        """
        # 创建用户和审核员
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        reviewer = Users.objects.create(
            username=f'reviewer_{uuid.uuid4().hex[:8]}',
            password='test_password',
            is_staff=True
        )

        # 创建多条待审核内容
        content_ids = []
        for i in range(count):
            if content_type == 'knowledge':
                content = KnowledgeBase.objects.create(
                    name=f'{name}_{i}',
                    description=description,
                    uploader=user,
                    is_pending=True,
                    is_public=False,
                    rejection_reason='旧的拒绝原因'
                )
            else:
                content = PersonaCard.objects.create(
                    name=f'{name}_{i}',
                    description=description,
                    uploader=user,
                    is_pending=True,
                    is_public=False,
                    rejection_reason='旧的拒绝原因'
                )

            # 创建上传记录
            UploadRecord.objects.create(
                uploader=user,
                target_id=str(content.id),
                target_type=content_type,
                name=content.name,
                description=content.description,
                status='pending'
            )
            content_ids.append(str(content.id))

        # 执行批量审核通过
        result = ReviewService.batch_approve(content_ids, content_type, reviewer)

        # 验证所有成功项的状态
        self.assertEqual(result['success_count'], count, "所有项应成功")
        self.assertEqual(result['fail_count'], 0, "不应有失败项")

        # 逐条验证状态变更
        model_class = KnowledgeBase if content_type == 'knowledge' else PersonaCard
        for cid in content_ids:
            content = model_class.objects.get(id=cid)
            self.assertFalse(content.is_pending, "批量通过后 is_pending 应为 False")
            self.assertTrue(content.is_public, "批量通过后 is_public 应为 True")
            self.assertIsNone(
                content.rejection_reason,
                "批量通过后 rejection_reason 应为 null"
            )


class ReviewBatchResultConsistencyPropertyTest(TestCase):
    """批量操作结果一致性属性测试

    **属性 12：批量操作结果一致性**
    **Validates: Requirements 6.2, 6.3**

    验证批量操作返回的结果一致性：
    - success_count + fail_count == len(ids)
    - failures 长度 == fail_count
    - 每条 failure 包含 id 和 reason
    """

    @given(
        name=valid_content_name,
        description=valid_description,
        content_type=content_type_strategy,
        valid_count=st.integers(min_value=1, max_value=3),
        invalid_count=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_12_batch_result_consistency(
        self, name, description, content_type, valid_count, invalid_count
    ):
        """属性 12：批量操作结果一致性

        **Validates: Requirements 6.2, 6.3**

        对于任意一组 ID（包含有效和无效的 ID），批量操作返回的
        success_count + fail_count 应等于 ids 列表的长度，
        且 failures 数组的长度应等于 fail_count，
        每条 failure 包含 id 和 reason。
        """
        # 创建用户和审核员
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        reviewer = Users.objects.create(
            username=f'reviewer_{uuid.uuid4().hex[:8]}',
            password='test_password',
            is_staff=True
        )

        # 创建有效的待审核内容
        valid_ids = []
        for i in range(valid_count):
            if content_type == 'knowledge':
                content = KnowledgeBase.objects.create(
                    name=f'{name}_valid_{i}',
                    description=description,
                    uploader=user,
                    is_pending=True,
                    is_public=False
                )
            else:
                content = PersonaCard.objects.create(
                    name=f'{name}_valid_{i}',
                    description=description,
                    uploader=user,
                    is_pending=True,
                    is_public=False
                )

            UploadRecord.objects.create(
                uploader=user,
                target_id=str(content.id),
                target_type=content_type,
                name=content.name,
                description=content.description,
                status='pending'
            )
            valid_ids.append(str(content.id))

        # 生成无效的 ID（不存在的内容）
        invalid_ids = [str(uuid.uuid4()) for _ in range(invalid_count)]

        # 合并所有 ID
        all_ids = valid_ids + invalid_ids
        total_count = len(all_ids)

        # 执行批量审核通过
        result = ReviewService.batch_approve(all_ids, content_type, reviewer)

        # 验证 success_count + fail_count == len(ids)
        self.assertEqual(
            result['success_count'] + result['fail_count'],
            total_count,
            f"success_count ({result['success_count']}) + fail_count ({result['fail_count']}) "
            f"应等于 ids 总数 ({total_count})"
        )

        # 验证 failures 长度 == fail_count
        self.assertEqual(
            len(result['failures']),
            result['fail_count'],
            f"failures 长度 ({len(result['failures'])}) 应等于 fail_count ({result['fail_count']})"
        )

        # 验证每条 failure 包含 id 和 reason
        for failure in result['failures']:
            self.assertIn('id', failure, "每条 failure 应包含 id 字段")
            self.assertIn('reason', failure, "每条 failure 应包含 reason 字段")

    @given(
        name=valid_content_name,
        description=valid_description,
        content_type=content_type_strategy,
        valid_count=st.integers(min_value=1, max_value=3),
        invalid_count=st.integers(min_value=1, max_value=3),
        reason=rejection_reason_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_12_batch_reject_result_consistency(
        self, name, description, content_type, valid_count, invalid_count, reason
    ):
        """属性 12：批量拒绝操作结果一致性

        **Validates: Requirements 6.2, 6.3**

        对于任意一组 ID（包含有效和无效的 ID），batch_reject 返回的
        success_count + fail_count 应等于 ids 列表的长度，
        且 failures 数组的长度应等于 fail_count。
        """
        # 创建用户和审核员
        user = Users.objects.create(
            username=f'user_{uuid.uuid4().hex[:8]}',
            password='test_password'
        )
        reviewer = Users.objects.create(
            username=f'reviewer_{uuid.uuid4().hex[:8]}',
            password='test_password',
            is_staff=True
        )

        # 创建有效的待审核内容
        valid_ids = []
        for i in range(valid_count):
            if content_type == 'knowledge':
                content = KnowledgeBase.objects.create(
                    name=f'{name}_valid_{i}',
                    description=description,
                    uploader=user,
                    is_pending=True,
                    is_public=False
                )
            else:
                content = PersonaCard.objects.create(
                    name=f'{name}_valid_{i}',
                    description=description,
                    uploader=user,
                    is_pending=True,
                    is_public=False
                )

            UploadRecord.objects.create(
                uploader=user,
                target_id=str(content.id),
                target_type=content_type,
                name=content.name,
                description=content.description,
                status='pending'
            )
            valid_ids.append(str(content.id))

        # 生成无效的 ID
        invalid_ids = [str(uuid.uuid4()) for _ in range(invalid_count)]

        # 合并所有 ID
        all_ids = valid_ids + invalid_ids
        total_count = len(all_ids)

        # 执行批量审核拒绝
        result = ReviewService.batch_reject(all_ids, content_type, reviewer, reason)

        # 验证 success_count + fail_count == len(ids)
        self.assertEqual(
            result['success_count'] + result['fail_count'],
            total_count,
            f"success_count ({result['success_count']}) + fail_count ({result['fail_count']}) "
            f"应等于 ids 总数 ({total_count})"
        )

        # 验证 failures 长度 == fail_count
        self.assertEqual(
            len(result['failures']),
            result['fail_count'],
            f"failures 长度 ({len(result['failures'])}) 应等于 fail_count ({result['fail_count']})"
        )

        # 验证每条 failure 包含 id 和 reason
        for failure in result['failures']:
            self.assertIn('id', failure, "每条 failure 应包含 id 字段")
            self.assertIn('reason', failure, "每条 failure 应包含 reason 字段")

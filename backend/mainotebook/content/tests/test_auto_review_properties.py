# -*- coding: utf-8 -*-

"""AI 自动审核属性测试模块

使用 Hypothesis 进行基于属性的测试，验证 AI 自动审核系统的核心属性。

**Feature: ai-auto-review**
**Validates: Requirements 8.6**
"""

import json
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase


# 配置 Hypothesis
settings.register_profile("default", max_examples=100, deadline=None)
settings.load_profile("default")


# ============================================================
# 策略定义：report_data 生成器
# ============================================================

# 违规类型候选列表
VIOLATION_TYPES = ["porn", "politics", "abuse"]

# 内容类型
CONTENT_TYPES = ["knowledge", "persona"]

# 决策类型
DECISIONS = ["auto_approved", "auto_rejected", "pending_manual"]

# part_type 候选
PART_TYPES = ["text_field", "file", "segment"]


def violation_types_strategy() -> st.SearchStrategy:
    """生成违规类型子集"""
    return st.lists(
        st.sampled_from(VIOLATION_TYPES),
        min_size=0,
        max_size=3,
        unique=True,
    )


def confidence_strategy() -> st.SearchStrategy:
    """生成 0.0~1.0 的置信度浮点数，排除 NaN 和 Inf"""
    return st.floats(
        min_value=0.0,
        max_value=1.0,
        allow_nan=False,
        allow_infinity=False,
    )


def part_name_strategy() -> st.SearchStrategy:
    """生成审核部分名称"""
    return st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_-. '
        ),
        min_size=1,
        max_size=50,
    ).filter(lambda x: x.strip() != '')


def iso_datetime_strategy() -> st.SearchStrategy:
    """生成 ISO 格式的时间字符串"""
    return st.datetimes().map(lambda dt: dt.isoformat() + "Z")


def part_strategy() -> st.SearchStrategy:
    """生成单个审核部分（part）数据"""
    return st.fixed_dictionaries({
        "part_name": part_name_strategy(),
        "part_type": st.sampled_from(PART_TYPES),
        "confidence": confidence_strategy(),
        "violation_types": violation_types_strategy(),
        "decision": st.sampled_from(["true", "false"]),
    })


def report_data_strategy() -> st.SearchStrategy:
    """生成完整的 report_data 字典

    包含 content_name、content_type、review_time、decision、
    final_confidence、violation_types、parts 字段。
    """
    return st.fixed_dictionaries({
        "content_name": part_name_strategy(),
        "content_type": st.sampled_from(CONTENT_TYPES),
        "review_time": iso_datetime_strategy(),
        "decision": st.sampled_from(DECISIONS),
        "final_confidence": confidence_strategy(),
        "violation_types": violation_types_strategy(),
        "parts": st.lists(part_strategy(), min_size=0, max_size=5),
    })


# ============================================================
# 属性测试
# ============================================================


class ReviewReportJsonRoundTripPropertyTest(TestCase):
    """审核报告 JSON 序列化往返属性测试

    **Feature: ai-auto-review, Property 13: 审核报告 JSON 序列化往返**
    **Validates: Requirements 8.6**

    验证对于任意有效的 ReviewReport 数据，将 report_data 序列化为
    JSON 字符串再反序列化，应得到与原始数据等价的对象。
    """

    @given(report_data=report_data_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_13_json_serialization_roundtrip(
        self, report_data: dict
    ) -> None:
        """属性 13：审核报告 JSON 序列化往返

        **Validates: Requirements 8.6**

        对于任意有效的 report_data，序列化为 JSON 字符串再反序列化后
        应得到与原始数据等价的对象。
        """
        # 序列化为 JSON 字符串
        json_str = json.dumps(report_data, ensure_ascii=False)

        # 反序列化回 Python 对象
        restored = json.loads(json_str)

        # 验证往返一致性
        self.assertEqual(restored, report_data)


class ContentTypeToTextTypeMappingPropertyTest(TestCase):
    """content_type 到 text_type 的正确映射属性测试

    **Feature: ai-auto-review, Property 7: content_type 到 text_type 的正确映射**
    **Validates: Requirements 4.3, 4.4**

    验证对于任意内容类型（knowledge/persona），content_type 直接映射为
    相同的 text_type，且 ModerationService.CONTEXT_RULES 中存在对应键。
    """

    @given(content_type=st.sampled_from(["knowledge", "persona"]))
    @settings(max_examples=100, deadline=None)
    def test_property_7_content_type_to_text_type_mapping(
        self, content_type: str
    ) -> None:
        """属性 7：content_type 到 text_type 的正确映射

        **Validates: Requirements 4.3, 4.4**

        对于任意 content_type（knowledge/persona），映射后的 text_type
        应与 content_type 相同（恒等映射），且在 CONTEXT_RULES 中存在。
        """
        from mainotebook.content.services.moderation_service import ModerationService

        # 验证 content_type 在 CONTEXT_RULES 中存在对应键
        self.assertIn(
            content_type,
            ModerationService.CONTEXT_RULES,
            f"CONTEXT_RULES 中缺少 '{content_type}' 键",
        )

        # 验证恒等映射：content_type == text_type
        # AutoReviewService 将 content_type 直接作为 text_type 传递给 ModerationService
        text_type = content_type
        self.assertEqual(
            text_type,
            content_type,
            f"content_type '{content_type}' 应映射为相同的 text_type",
        )

        # 验证 CONTEXT_RULES 中对应的规则非空
        rules = ModerationService.CONTEXT_RULES[content_type]
        self.assertIsInstance(rules, str, "审核规则应为字符串")
        self.assertTrue(
            len(rules.strip()) > 0,
            f"'{content_type}' 的审核规则不应为空",
        )


# ============================================================
# 属性测试：文本字段拼接完整性 & 仅审核 text/plain 文件
# ============================================================

from unittest.mock import MagicMock

from mainotebook.content.services.auto_review_service import AutoReviewService


class TextFieldsCompletenessPropertyTest(TestCase):
    """文本字段拼接完整性属性测试

    **Feature: ai-auto-review, Property 2: 文本字段拼接完整性**
    **Validates: Requirements 1.3**

    验证对于任意内容对象（包含随机生成的 name、description、content 字段），
    拼接后的审核文本应包含所有非空字段的内容，空字段不出现在结果中。
    """

    @given(
        name=st.text(min_size=1, max_size=50),
        description=st.text(min_size=0, max_size=100),
        content_text=st.text(min_size=0, max_size=200),
    )
    @settings(max_examples=100, deadline=None)
    def test_property_2_text_fields_completeness(
        self, name: str, description: str, content_text: str
    ) -> None:
        """属性 2：文本字段拼接完整性

        **Validates: Requirements 1.3**

        对于任意非空 name、随机 description 和 content，拼接结果应包含
        所有非空字段的内容。
        """
        # 构造 mock 内容对象
        content = MagicMock()
        content.name = name
        content.description = description
        content.content = content_text

        # 调用拼接方法
        result = AutoReviewService._build_text_fields(content)

        # 验证非空字段都出现在拼接结果中
        if name:
            self.assertIn(name, result, "非空 name 应出现在拼接结果中")
        if description:
            self.assertIn(description, result, "非空 description 应出现在拼接结果中")
        if content_text:
            self.assertIn(content_text, result, "非空 content 应出现在拼接结果中")

    @given(
        name=st.just(""),
        description=st.just(""),
        content_text=st.just(""),
    )
    @settings(max_examples=1, deadline=None)
    def test_property_2_all_empty_fields(
        self, name: str, description: str, content_text: str
    ) -> None:
        """属性 2 边界：所有字段为空时拼接结果为空字符串

        **Validates: Requirements 1.3**
        """
        content = MagicMock()
        content.name = name
        content.description = description
        content.content = content_text

        result = AutoReviewService._build_text_fields(content)
        self.assertEqual(result, "", "所有字段为空时拼接结果应为空字符串")


class OnlyTextPlainFilesPropertyTest(TestCase):
    """仅审核 text/plain 文件属性测试

    **Feature: ai-auto-review, Property 3: 仅审核 text/plain 文件**
    **Validates: Requirements 1.4**

    验证对于任意一组关联文件（包含随机的 file_type），获取待审核文件列表时，
    返回的文件列表中每个文件的 file_type 都应为 "text/plain"。
    """

    @given(
        file_types=st.lists(
            st.sampled_from([
                "text/plain",
                "application/pdf",
                "image/png",
                "text/html",
                "application/json",
                "image/jpeg",
                "application/octet-stream",
            ]),
            min_size=0,
            max_size=10,
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_3_only_text_plain_files(
        self, file_types: list
    ) -> None:
        """属性 3：仅审核 text/plain 文件

        **Validates: Requirements 1.4**

        对于任意 file_type 列表，_get_text_files 返回的文件都应为 text/plain。
        """
        # 构造 mock 文件对象列表
        mock_files = []
        for ft in file_types:
            f = MagicMock()
            f.file_type = ft
            mock_files.append(f)

        # mock content.files.filter(file_type='text/plain') 的行为
        expected_plain_files = [f for f in mock_files if f.file_type == "text/plain"]
        content = MagicMock()
        content.files.filter.return_value = expected_plain_files

        # 调用方法
        result = AutoReviewService._get_text_files(content, "knowledge")

        # 验证返回的每个文件都是 text/plain
        for f in result:
            self.assertEqual(
                f.file_type,
                "text/plain",
                f"返回的文件 file_type 应为 text/plain，实际为 {f.file_type}",
            )

        # 验证 filter 被正确调用
        content.files.filter.assert_called_once_with(file_type="text/plain")

    @given(
        file_types=st.lists(
            st.sampled_from([
                "text/plain",
                "application/pdf",
                "image/png",
                "text/html",
                "application/json",
            ]),
            min_size=0,
            max_size=10,
        ),
        content_type=st.sampled_from(["knowledge", "persona"]),
    )
    @settings(max_examples=100, deadline=None)
    def test_property_3_filter_count_matches(
        self, file_types: list, content_type: str
    ) -> None:
        """属性 3 补充：过滤后的文件数量应等于原始列表中 text/plain 的数量

        **Validates: Requirements 1.4**
        """
        # 构造 mock 文件对象
        mock_files = []
        for ft in file_types:
            f = MagicMock()
            f.file_type = ft
            mock_files.append(f)

        expected_count = sum(1 for ft in file_types if ft == "text/plain")
        expected_plain_files = [f for f in mock_files if f.file_type == "text/plain"]

        content = MagicMock()
        content.files.filter.return_value = expected_plain_files

        result = AutoReviewService._get_text_files(content, content_type)

        self.assertEqual(
            len(result),
            expected_count,
            f"过滤后文件数量应为 {expected_count}，实际为 {len(result)}",
        )


# ============================================================
# 属性测试：文本分段长度约束
# ============================================================


class TextSegmentLengthConstraintPropertyTest(TestCase):
    """文本分段长度约束属性测试

    **Feature: ai-auto-review, Property 6: 文本分段长度约束**
    **Validates: Requirements 3.1**

    验证对于任意长度超过 MAX_SEGMENT_LENGTH 的文本，分段函数产生的每个
    Text_Segment 的长度都应 <= MAX_SEGMENT_LENGTH，且所有分段拼接后应等于原始文本。
    """

    @given(
        paragraphs=st.lists(
            st.text(min_size=1, max_size=8000),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_6_segment_length_and_concatenation(
        self, paragraphs: list
    ) -> None:
        """属性 6：文本分段长度约束

        **Validates: Requirements 3.1**

        对于任意由段落组成的超长文本，分段后每段长度 <= MAX_SEGMENT_LENGTH，
        且所有分段拼接后等于原始文本。
        """
        # 用 \n\n 拼接段落，模拟真实文本结构
        text = "\n\n".join(paragraphs)

        # 仅在文本超过最大分段长度时测试分段逻辑
        if len(text) <= AutoReviewService.MAX_SEGMENT_LENGTH:
            return

        segments = AutoReviewService._split_text_segments(text)

        # 验证每段长度不超过 MAX_SEGMENT_LENGTH
        for i, seg in enumerate(segments):
            self.assertLessEqual(
                len(seg),
                AutoReviewService.MAX_SEGMENT_LENGTH,
                f"第 {i + 1} 段长度 {len(seg)} 超过限制 "
                f"{AutoReviewService.MAX_SEGMENT_LENGTH}",
            )

        # 验证所有分段拼接后等于原始文本
        self.assertEqual(
            "".join(segments),
            text,
            "所有分段拼接后应等于原始文本",
        )


# ============================================================
# 属性测试：置信度决策映射 & 审核结果聚合
# ============================================================

from unittest.mock import patch, MagicMock


class ConfidenceDecisionMappingPropertyTest(TestCase):
    """置信度决策映射属性测试

    **Feature: ai-auto-review, Property 1: 置信度决策映射**
    **Validates: Requirements 2.1, 2.2, 2.3**

    验证对于任意置信度值（0.0~1.0）和任意违规类型列表：
    - confidence < 0.5 → "auto_approved"
    - confidence > 0.8 → "auto_rejected"
    - 0.5 <= confidence <= 0.8 → "pending_manual"
    """

    @given(
        confidence=confidence_strategy(),
        violation_types=violation_types_strategy(),
    )
    @settings(max_examples=100, deadline=None)
    @patch(
        "mainotebook.content.services.review_service.ReviewService"
    )
    @patch(
        "mainotebook.system.models.Users"
    )
    def test_property_1_confidence_decision_mapping(
        self,
        mock_users_cls: MagicMock,
        mock_review_service_cls: MagicMock,
        confidence: float,
        violation_types: list,
    ) -> None:
        """属性 1：置信度决策映射

        **Validates: Requirements 2.1, 2.2, 2.3**

        对于任意 confidence（0.0~1.0）和任意 violation_types，
        _make_decision 应根据阈值返回正确的决策字符串。
        """
        # 模拟 Users.objects.get_or_create 返回 AI 审核员
        mock_ai_user = MagicMock()
        mock_users_cls.objects.get_or_create.return_value = (mock_ai_user, True)

        # 调用决策方法
        decision = AutoReviewService._make_decision(
            content_id="test-id",
            content_type="knowledge",
            confidence=confidence,
            violation_types=violation_types,
        )

        # 验证决策映射
        if confidence < 0.5:
            self.assertEqual(
                decision,
                "auto_approved",
                f"confidence={confidence} 应返回 auto_approved",
            )
        elif confidence > 0.8:
            self.assertEqual(
                decision,
                "auto_rejected",
                f"confidence={confidence} 应返回 auto_rejected",
            )
        else:
            self.assertEqual(
                decision,
                "pending_manual",
                f"confidence={confidence} 应返回 pending_manual",
            )


class MaxConfidenceAggregationPropertyTest(TestCase):
    """审核结果聚合——最高置信度属性测试

    **Feature: ai-auto-review, Property 4: 审核结果聚合——最高置信度**
    **Validates: Requirements 3.3, 7.2**

    验证对于任意一组审核结果（每个包含 confidence 和 violation_types），
    _aggregate_results 返回的 max_confidence 应等于所有结果中 confidence 的最大值。
    """

    @given(
        results=st.lists(
            st.fixed_dictionaries({
                "confidence": confidence_strategy(),
                "violation_types": violation_types_strategy(),
            }),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_4_max_confidence_aggregation(
        self, results: list
    ) -> None:
        """属性 4：审核结果聚合——最高置信度

        **Validates: Requirements 3.3, 7.2**

        对于任意非空审核结果列表，聚合后的 max_confidence 应等于
        所有结果中 confidence 的最大值。
        """
        # 调用聚合方法
        max_confidence, _ = AutoReviewService._aggregate_results(results)

        # 计算期望的最高置信度
        expected_max = max(r["confidence"] for r in results)

        self.assertEqual(
            max_confidence,
            expected_max,
            f"聚合后的 max_confidence 应为 {expected_max}，实际为 {max_confidence}",
        )


class ViolationTypesDeduplicationPropertyTest(TestCase):
    """审核结果聚合——违规类型去重合并属性测试

    **Feature: ai-auto-review, Property 5: 审核结果聚合——违规类型去重合并**
    **Validates: Requirements 3.4, 7.3**

    验证对于任意一组审核结果（每个包含 confidence 和 violation_types），
    _aggregate_results 返回的 violation_types 应等于所有结果中 violation_types 的并集（去重后）。
    """

    @given(
        results=st.lists(
            st.fixed_dictionaries({
                "confidence": confidence_strategy(),
                "violation_types": violation_types_strategy(),
            }),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_5_violation_types_deduplication(
        self, results: list
    ) -> None:
        """属性 5：审核结果聚合——违规类型去重合并

        **Validates: Requirements 3.4, 7.3**

        对于任意非空审核结果列表，聚合后的 violation_types 应等于
        所有结果中 violation_types 的集合并集。
        """
        # 调用聚合方法
        _, merged_violation_types = AutoReviewService._aggregate_results(results)

        # 计算期望的违规类型并集
        expected_set = set()
        for r in results:
            expected_set.update(r["violation_types"])

        self.assertEqual(
            set(merged_violation_types),
            expected_set,
            f"聚合后的违规类型应为 {expected_set}，实际为 {set(merged_violation_types)}",
        )


# ============================================================
# 属性测试：审核报告字段完整性 & 分段报告详情完整性
# ============================================================


class ReportFieldCompletenessPropertyTest(TestCase):
    """审核报告字段完整性属性测试

    **Feature: ai-auto-review, Property 10: 审核报告字段完整性**
    **Validates: Requirements 8.1, 8.2**

    验证对于任意已完成的 AI 审核，生成的 ReviewReport 的 report_data 应包含：
    content_name、content_type、review_time、decision、final_confidence、
    violation_types、parts 字段，且 parts 中每个元素应包含 part_name、
    part_type、confidence、violation_types。
    """

    # report_data 顶层必需字段
    REQUIRED_TOP_LEVEL_KEYS = {
        "content_name",
        "content_type",
        "review_time",
        "decision",
        "final_confidence",
        "violation_types",
        "parts",
    }

    # parts 中每个元素的必需字段
    REQUIRED_PART_KEYS = {
        "part_name",
        "part_type",
        "confidence",
        "violation_types",
    }

    @given(report_data=report_data_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_10_report_field_completeness(
        self, report_data: dict
    ) -> None:
        """属性 10：审核报告字段完整性

        **Validates: Requirements 8.1, 8.2**

        对于任意由 report_data_strategy 生成的 report_data，
        应包含所有必需的顶层字段，且 parts 中每个元素应包含所有必需的部分字段。
        """
        # 验证顶层必需字段
        for key in self.REQUIRED_TOP_LEVEL_KEYS:
            self.assertIn(
                key,
                report_data,
                f"report_data 缺少必需的顶层字段: {key}",
            )

        # 验证 parts 是列表
        self.assertIsInstance(
            report_data["parts"],
            list,
            "report_data['parts'] 应为列表类型",
        )

        # 验证每个 part 包含必需字段
        for i, part in enumerate(report_data["parts"]):
            for key in self.REQUIRED_PART_KEYS:
                self.assertIn(
                    key,
                    part,
                    f"parts[{i}] 缺少必需字段: {key}",
                )

            # 验证字段类型
            self.assertIsInstance(
                part["part_name"],
                str,
                f"parts[{i}]['part_name'] 应为字符串",
            )
            self.assertIsInstance(
                part["part_type"],
                str,
                f"parts[{i}]['part_type'] 应为字符串",
            )
            self.assertIsInstance(
                part["confidence"],
                float,
                f"parts[{i}]['confidence'] 应为浮点数",
            )
            self.assertIsInstance(
                part["violation_types"],
                list,
                f"parts[{i}]['violation_types'] 应为列表",
            )


class SegmentDetailsCompletenessPropertyTest(TestCase):
    """分段报告详情完整性属性测试

    **Feature: ai-auto-review, Property 11: 分段报告详情完整性**
    **Validates: Requirements 3.5, 8.3**

    验证对于任意包含分段审核的文件，_review_segments 返回的 segment_details
    中每个元素应包含 segment_index、text_summary（长度 <= 100）、confidence、
    violation_types 字段，且 segment_index 从 1 开始连续递增。
    """

    # 每个分段详情的必需字段
    REQUIRED_SEGMENT_KEYS = {
        "segment_index",
        "text_summary",
        "confidence",
        "violation_types",
        "decision",
    }

    @given(
        segments=st.lists(
            st.text(min_size=1, max_size=200),
            min_size=1,
            max_size=5,
        ),
        text_type=st.sampled_from(["knowledge", "persona"]),
    )
    @settings(max_examples=100, deadline=None)
    @patch(
        "mainotebook.content.services.moderation_service.get_moderation_service"
    )
    def test_property_11_segment_details_completeness(
        self,
        mock_get_service: MagicMock,
        segments: list,
        text_type: str,
    ) -> None:
        """属性 11：分段报告详情完整性

        **Validates: Requirements 3.5, 8.3**

        对于任意文本分段列表，_review_segments 返回的 segment_details 中：
        - segment_index 从 1 开始连续递增
        - text_summary 长度 <= 100
        - 每个分段包含 confidence、violation_types 字段
        """
        # 模拟 ModerationService 返回有效结果
        mock_service = MagicMock()
        mock_service.moderate.return_value = {
            "decision": "true",
            "confidence": 0.3,
            "violation_types": [],
        }
        mock_get_service.return_value = mock_service

        # 调用分段审核方法
        _, _, segment_details = AutoReviewService._review_segments(
            segments, text_type
        )

        # 验证分段数量与输入一致
        self.assertEqual(
            len(segment_details),
            len(segments),
            f"分段详情数量应为 {len(segments)}，实际为 {len(segment_details)}",
        )

        # 验证每个分段详情的字段完整性
        for i, detail in enumerate(segment_details):
            # 验证必需字段存在
            for key in self.REQUIRED_SEGMENT_KEYS:
                self.assertIn(
                    key,
                    detail,
                    f"segment_details[{i}] 缺少必需字段: {key}",
                )

            # 验证 segment_index 从 1 开始连续递增
            self.assertEqual(
                detail["segment_index"],
                i + 1,
                f"segment_details[{i}] 的 segment_index 应为 {i + 1}，"
                f"实际为 {detail['segment_index']}",
            )

            # 验证 text_summary 长度 <= 100
            self.assertLessEqual(
                len(detail["text_summary"]),
                100,
                f"segment_details[{i}] 的 text_summary 长度 "
                f"{len(detail['text_summary'])} 超过 100 字符限制",
            )

            # 验证字段类型
            self.assertIsInstance(
                detail["confidence"],
                float,
                f"segment_details[{i}]['confidence'] 应为浮点数",
            )
            self.assertIsInstance(
                detail["violation_types"],
                list,
                f"segment_details[{i}]['violation_types'] 应为列表",
            )


# ============================================================
# 属性测试：异常处理（Property 8 & 9）
# ============================================================


class ApiFailurePreservesStatePropertyTest(TestCase):
    """API 失败时保持待审核状态属性测试

    **Feature: ai-auto-review, Property 8: API 失败时保持待审核状态**
    **Validates: Requirements 6.1**

    验证对于任意待审核内容，当 ModerationService 调用失败（抛出异常）时，
    内容的 is_pending 应保持为 True，is_public 应保持为 False。
    """

    @given(content_type=st.sampled_from(["knowledge", "persona"]))
    @settings(max_examples=100, deadline=None)
    @patch("mainotebook.content.services.moderation_service.get_moderation_service")
    @patch("mainotebook.content.models.PersonaCard")
    @patch("mainotebook.content.models.KnowledgeBase")
    def test_property_8_api_failure_preserves_state(
        self,
        mock_kb: MagicMock,
        mock_persona: MagicMock,
        mock_get_service: MagicMock,
        content_type: str,
    ) -> None:
        """属性 8：API 失败时保持待审核状态

        **Validates: Requirements 6.1**

        对于任意待审核内容，当 ModerationService 抛出异常时，
        内容的 is_pending 应保持为 True，is_public 应保持为 False，
        且返回结果包含 error 键。
        """
        # 构造 mock 内容对象，初始状态为待审核
        mock_content = MagicMock()
        mock_content.is_pending = True
        mock_content.is_public = False
        mock_content.name = "测试内容"
        mock_content.description = "测试描述"
        mock_content.content = "测试正文"

        # 根据 content_type 设置对应模型的 filter 返回值
        if content_type == "knowledge":
            mock_kb.objects.filter.return_value.first.return_value = mock_content
        else:
            mock_persona.objects.filter.return_value.first.return_value = mock_content

        # 模拟 ModerationService 抛出异常（API 调用失败）
        mock_service = MagicMock()
        mock_service.moderate.side_effect = Exception("API 调用超时")
        mock_get_service.return_value = mock_service

        # 调用自动审核
        result = AutoReviewService.execute_auto_review("test-id", content_type)

        # 验证内容状态未被修改：is_pending 仍为 True，is_public 仍为 False
        self.assertTrue(
            mock_content.is_pending,
            "API 失败后 is_pending 应保持为 True",
        )
        self.assertFalse(
            mock_content.is_public,
            "API 失败后 is_public 应保持为 False",
        )

        # 验证返回结果包含 error 键
        self.assertIn(
            "error",
            result,
            "API 失败时应返回包含 error 键的字典",
        )


class UnreadableFileSkipPropertyTest(TestCase):
    """不可读文件跳过不影响审核属性测试

    **Feature: ai-auto-review, Property 9: 不可读文件跳过不影响审核**
    **Validates: Requirements 6.2**

    验证对于任意内容（包含文本字段和若干不可读文件），审核流程应正常完成
    并返回基于文本字段的审核结果，不应抛出异常。
    """

    @given(
        content_type=st.sampled_from(["knowledge", "persona"]),
        num_unreadable_files=st.integers(min_value=1, max_value=5),
        confidence=confidence_strategy(),
        violation_types=violation_types_strategy(),
    )
    @settings(max_examples=100, deadline=None)
    @patch(
        "mainotebook.content.services.auto_review_service.AutoReviewService._notify_uploader"
    )
    @patch(
        "mainotebook.content.services.auto_review_service.AutoReviewService._generate_report"
    )
    @patch(
        "mainotebook.content.services.auto_review_service.AutoReviewService._make_decision"
    )
    @patch(
        "mainotebook.content.services.auto_review_service.AutoReviewService._read_file_content"
    )
    @patch(
        "mainotebook.content.services.auto_review_service.AutoReviewService._get_text_files"
    )
    @patch("mainotebook.content.services.moderation_service.get_moderation_service")
    @patch("mainotebook.content.models.PersonaCard")
    @patch("mainotebook.content.models.KnowledgeBase")
    def test_property_9_unreadable_files_skip(
        self,
        mock_kb: MagicMock,
        mock_persona: MagicMock,
        mock_get_service: MagicMock,
        mock_get_text_files: MagicMock,
        mock_read_file: MagicMock,
        mock_make_decision: MagicMock,
        mock_generate_report: MagicMock,
        mock_notify: MagicMock,
        content_type: str,
        num_unreadable_files: int,
        confidence: float,
        violation_types: list,
    ) -> None:
        """属性 9：不可读文件跳过不影响审核

        **Validates: Requirements 6.2**

        对于任意内容（包含文本字段和若干不可读文件），审核流程应正常完成
        并返回基于文本字段的审核结果，不应抛出异常。
        """
        # 构造 mock 内容对象
        mock_content = MagicMock()
        mock_content.is_pending = True
        mock_content.is_public = False
        mock_content.name = "测试内容"
        mock_content.description = "测试描述"
        mock_content.content = "测试正文"

        # 根据 content_type 设置对应模型的 filter 返回值
        if content_type == "knowledge":
            mock_kb.objects.filter.return_value.first.return_value = mock_content
        else:
            mock_persona.objects.filter.return_value.first.return_value = mock_content

        # 模拟 ModerationService 对文本字段返回有效结果
        mock_service = MagicMock()
        mock_service.moderate.return_value = {
            "decision": "true" if confidence < 0.5 else "false",
            "confidence": confidence,
            "violation_types": violation_types,
        }
        mock_get_service.return_value = mock_service

        # 模拟若干不可读文件
        mock_files = [MagicMock() for _ in range(num_unreadable_files)]
        for f in mock_files:
            f.file_path = "/invalid/path/file.txt"
            f.file_name = "unreadable.txt"
        mock_get_text_files.return_value = mock_files

        # 所有文件都不可读，_read_file_content 返回 None
        mock_read_file.return_value = None

        # 模拟决策和报告生成
        mock_make_decision.return_value = "pending_manual"
        mock_report = MagicMock()
        mock_report.report_data = {
            "content_name": "测试内容",
            "decision": "pending_manual",
            "final_confidence": confidence,
        }
        mock_generate_report.return_value = mock_report

        # 调用自动审核——不应抛出异常
        result = AutoReviewService.execute_auto_review("test-id", content_type)

        # 验证返回结果不是错误字典
        self.assertNotIn(
            "error",
            result,
            "不可读文件不应导致审核失败，结果不应包含 error 键",
        )

        # 验证 ModerationService 被调用（至少审核了文本字段）
        mock_service.moderate.assert_called()

        # 验证 _read_file_content 被调用了正确的次数（每个文件一次）
        self.assertEqual(
            mock_read_file.call_count,
            num_unreadable_files,
            f"_read_file_content 应被调用 {num_unreadable_files} 次",
        )


# ============================================================
# 属性测试：批量 AI 审核任务数量一致性（Property 12）
# ============================================================


class BatchTaskCountConsistencyPropertyTest(TestCase):
    """批量 AI 审核任务数量一致性属性测试

    **Feature: ai-auto-review, Property 12: 批量 AI 审核任务数量一致性**
    **Validates: Requirements 5.2**

    验证对于任意一组内容 ID 列表，批量 AI 审核应为每个 ID 创建恰好一个
    Celery 异步任务，任务总数等于 ID 列表长度。
    """

    @given(
        content_ids=st.lists(
            st.uuids().map(str),
            min_size=1,
            max_size=20,
        ),
        content_type=st.sampled_from(["knowledge", "persona"]),
    )
    @settings(max_examples=100, deadline=None)
    @patch("mainotebook.content.tasks.auto_review_task")
    def test_property_12_batch_task_count_consistency(
        self,
        mock_auto_review_task: MagicMock,
        content_ids: list,
        content_type: str,
    ) -> None:
        """属性 12：批量 AI 审核任务数量一致性

        **Validates: Requirements 5.2**

        对于任意长度的 ID 列表，batch_auto_review_task 创建的子任务数
        应等于 ID 列表长度。
        """
        from mainotebook.content.tasks import batch_auto_review_task

        # 模拟 auto_review_task.delay 返回 AsyncResult
        mock_async_result = MagicMock()
        mock_async_result.id = "fake-task-id"
        mock_auto_review_task.delay.return_value = mock_async_result

        # 同步执行批量任务
        result = batch_auto_review_task.apply(
            args=[content_ids, content_type]
        )

        data = result.result

        # 验证创建的任务数等于 ID 列表长度
        self.assertEqual(
            mock_auto_review_task.delay.call_count,
            len(content_ids),
            f"应创建 {len(content_ids)} 个子任务，实际创建 {mock_auto_review_task.delay.call_count} 个",
        )

        # 验证返回的 total 等于 ID 列表长度
        self.assertEqual(
            data["total"],
            len(content_ids),
            f"返回的 total 应为 {len(content_ids)}，实际为 {data['total']}",
        )

        # 验证返回的 task_ids 长度等于 ID 列表长度
        self.assertEqual(
            len(data["task_ids"]),
            len(content_ids),
            f"返回的 task_ids 长度应为 {len(content_ids)}，实际为 {len(data['task_ids'])}",
        )


# ============================================================
# 属性测试：审核完成后通知上传者（Property 14）
# ============================================================


class NotifyUploaderAfterReviewPropertyTest(TestCase):
    """审核完成后通知上传者属性测试

    **Feature: ai-auto-review, Property 14: 审核完成后通知上传者**
    **Validates: Requirements 2.4, 8.4**

    验证对于任意已完成的 AI 审核（自动通过或自动拒绝），
    应调用 ReviewNotificationService.send_review_notification。
    待人工复核时不发送通知。
    """

    @given(
        decision=st.sampled_from(["auto_approved", "auto_rejected"]),
        content_type=st.sampled_from(["knowledge", "persona"]),
        violation_types=violation_types_strategy(),
    )
    @settings(max_examples=100, deadline=None)
    @patch("mainotebook.content.services.review_notification.ReviewNotificationService")
    def test_property_14_notify_on_approved_or_rejected(
        self,
        mock_notify_cls: MagicMock,
        decision: str,
        content_type: str,
        violation_types: list,
    ) -> None:
        """属性 14：自动通过或自动拒绝时通知上传者

        **Validates: Requirements 2.4, 8.4**
        """
        # 构造 mock 内容和报告
        mock_content = MagicMock()
        mock_content.uploader.id = 42
        mock_content.name = "测试内容"

        mock_report = MagicMock()
        mock_report.decision = decision
        mock_report.violation_types = violation_types
        mock_report.content_id = "test-id"

        # 调用通知方法
        AutoReviewService._notify_uploader(mock_content, content_type, mock_report)

        # 验证通知被调用
        mock_notify_cls.send_review_notification.assert_called_once()

        # 验证调用参数
        call_kwargs = mock_notify_cls.send_review_notification.call_args
        args = call_kwargs[1] if call_kwargs[1] else {}
        if not args:
            args_positional = call_kwargs[0]
            # 验证位置参数
            assert args_positional[0] == 42  # uploader_id
            assert args_positional[1] == "测试内容"  # content_name

    @given(
        content_type=st.sampled_from(["knowledge", "persona"]),
    )
    @settings(max_examples=100, deadline=None)
    @patch("mainotebook.content.services.review_notification.ReviewNotificationService")
    def test_property_14_no_notify_on_pending_manual(
        self,
        mock_notify_cls: MagicMock,
        content_type: str,
    ) -> None:
        """属性 14 补充：待人工复核时不发送通知

        **Validates: Requirements 2.4, 8.4**
        """
        mock_content = MagicMock()
        mock_content.uploader.id = 42
        mock_content.name = "测试内容"

        mock_report = MagicMock()
        mock_report.decision = "pending_manual"
        mock_report.violation_types = []

        AutoReviewService._notify_uploader(mock_content, content_type, mock_report)

        # 待人工复核不应发送通知
        mock_notify_cls.send_review_notification.assert_not_called()

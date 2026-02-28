# -*- coding: utf-8 -*-

"""
ReviewReport 模型和序列化器单元测试

测试 ReviewReport 模型的创建、JSON 字段存储和读取、
ReviewReportSerializer 序列化输出、to_readable_text 方法。

验证需求：8.1, 8.2, 8.6
"""

import uuid
import json
from django.test import TestCase
from mainotebook.content.models import ReviewReport
from mainotebook.content.serializers.review import ReviewReportSerializer


class ReviewReportModelTest(TestCase):
    """ReviewReport 模型单元测试

    验证 ReviewReport 的创建、字段存储、__str__ 和 to_readable_text 方法。
    """

    def setUp(self):
        """测试前准备"""
        self.content_id = uuid.uuid4()
        self.report_data = {
            "content_name": "测试知识库",
            "content_type": "knowledge",
            "review_time": "2024-01-15T10:30:00Z",
            "decision": "auto_rejected",
            "final_confidence": 0.92,
            "violation_types": ["porn", "abuse"],
            "parts": [
                {
                    "part_name": "文本字段",
                    "part_type": "text_field",
                    "confidence": 0.15,
                    "violation_types": [],
                    "decision": "true"
                },
                {
                    "part_name": "example.txt",
                    "part_type": "file",
                    "confidence": 0.92,
                    "violation_types": ["porn", "abuse"],
                    "decision": "false",
                    "segments": [
                        {
                            "segment_index": 1,
                            "text_summary": "这是第一段的前100个字符...",
                            "confidence": 0.2,
                            "violation_types": [],
                            "decision": "true"
                        },
                        {
                            "segment_index": 2,
                            "text_summary": "这是第二段的前100个字符...",
                            "confidence": 0.92,
                            "violation_types": ["porn", "abuse"],
                            "decision": "false"
                        }
                    ]
                }
            ]
        }
        self.report = ReviewReport.objects.create(
            content_id=self.content_id,
            content_type="knowledge",
            content_name="测试知识库",
            decision="auto_rejected",
            final_confidence=0.92,
            violation_types=["porn", "abuse"],
            report_data=self.report_data,
        )

    def tearDown(self):
        """测试后清理"""
        ReviewReport.objects.all().delete()

    def test_create_review_report(self):
        """测试创建 ReviewReport 实例"""
        self.assertIsInstance(self.report.id, uuid.UUID)
        self.assertEqual(self.report.content_id, self.content_id)
        self.assertEqual(self.report.content_type, "knowledge")
        self.assertEqual(self.report.content_name, "测试知识库")
        self.assertEqual(self.report.decision, "auto_rejected")
        self.assertAlmostEqual(self.report.final_confidence, 0.92)
        self.assertIsNotNone(self.report.create_datetime)

    def test_json_field_violation_types(self):
        """测试 violation_types JSON 字段的存储和读取"""
        # 从数据库重新读取
        report = ReviewReport.objects.get(pk=self.report.pk)
        self.assertIsInstance(report.violation_types, list)
        self.assertEqual(report.violation_types, ["porn", "abuse"])

    def test_json_field_violation_types_empty(self):
        """测试 violation_types 为空列表时的存储和读取"""
        report = ReviewReport.objects.create(
            content_id=uuid.uuid4(),
            content_type="persona",
            content_name="测试人设卡",
            decision="auto_approved",
            final_confidence=0.1,
            violation_types=[],
            report_data={"parts": []},
        )
        report.refresh_from_db()
        self.assertEqual(report.violation_types, [])

    def test_json_field_report_data(self):
        """测试 report_data JSON 字段的存储和读取"""
        report = ReviewReport.objects.get(pk=self.report.pk)
        self.assertIsInstance(report.report_data, dict)
        self.assertEqual(report.report_data["content_name"], "测试知识库")
        self.assertIn("parts", report.report_data)
        self.assertEqual(len(report.report_data["parts"]), 2)

    def test_json_field_report_data_segments(self):
        """测试 report_data 中分段数据的存储和读取"""
        report = ReviewReport.objects.get(pk=self.report.pk)
        file_part = report.report_data["parts"][1]
        self.assertEqual(file_part["part_name"], "example.txt")
        self.assertIn("segments", file_part)
        self.assertEqual(len(file_part["segments"]), 2)
        self.assertEqual(file_part["segments"][0]["segment_index"], 1)
        self.assertEqual(file_part["segments"][1]["confidence"], 0.92)

    def test_json_serialization_roundtrip(self):
        """测试 report_data 的 JSON 序列化往返一致性"""
        report = ReviewReport.objects.get(pk=self.report.pk)
        # 序列化为 JSON 字符串再反序列化
        json_str = json.dumps(report.report_data, ensure_ascii=False)
        restored = json.loads(json_str)
        self.assertEqual(restored, self.report_data)

    def test_str_method(self):
        """测试 __str__ 方法"""
        result = str(self.report)
        # 应包含决策的中文显示和内容名称
        self.assertIn("自动拒绝", result)
        self.assertIn("测试知识库", result)
        self.assertIn("知识库", result)

    def test_str_method_all_decisions(self):
        """测试不同决策类型的 __str__ 输出"""
        decisions = {
            "auto_approved": "自动通过",
            "auto_rejected": "自动拒绝",
            "pending_manual": "待人工复核",
        }
        for decision_key, decision_label in decisions.items():
            report = ReviewReport.objects.create(
                content_id=uuid.uuid4(),
                content_type="knowledge",
                content_name="测试",
                decision=decision_key,
                final_confidence=0.5,
                violation_types=[],
                report_data={"parts": []},
            )
            self.assertIn(decision_label, str(report))

    def test_to_readable_text_contains_header(self):
        """测试 to_readable_text 包含报告标题"""
        text = self.report.to_readable_text()
        self.assertIn("AI 审核报告", text)

    def test_to_readable_text_contains_basic_info(self):
        """测试 to_readable_text 包含基本信息"""
        text = self.report.to_readable_text()
        self.assertIn("测试知识库", text)
        self.assertIn("知识库", text)
        self.assertIn("0.92", text)

    def test_to_readable_text_contains_decision(self):
        """测试 to_readable_text 包含决策结果"""
        text = self.report.to_readable_text()
        self.assertIn("自动拒绝", text)

    def test_to_readable_text_contains_violation_types(self):
        """测试 to_readable_text 包含违规类型"""
        text = self.report.to_readable_text()
        self.assertIn("色情", text)
        self.assertIn("辱骂", text)

    def test_to_readable_text_no_violations(self):
        """测试无违规类型时 to_readable_text 显示'无'"""
        report = ReviewReport.objects.create(
            content_id=uuid.uuid4(),
            content_type="persona",
            content_name="安全人设卡",
            decision="auto_approved",
            final_confidence=0.1,
            violation_types=[],
            report_data={"parts": []},
        )
        text = report.to_readable_text()
        self.assertIn("违规类型：无", text)

    def test_to_readable_text_contains_parts(self):
        """测试 to_readable_text 包含各审核部分详情"""
        text = self.report.to_readable_text()
        self.assertIn("文本字段", text)
        self.assertIn("example.txt", text)

    def test_to_readable_text_contains_segments(self):
        """测试 to_readable_text 包含分段审核详情"""
        text = self.report.to_readable_text()
        self.assertIn("第 1 段", text)
        self.assertIn("第 2 段", text)
        self.assertIn("这是第一段的前100个字符...", text)

    def test_to_readable_text_auto_approved(self):
        """测试自动通过决策的 to_readable_text"""
        report = ReviewReport.objects.create(
            content_id=uuid.uuid4(),
            content_type="knowledge",
            content_name="安全知识库",
            decision="auto_approved",
            final_confidence=0.1,
            violation_types=[],
            report_data={"parts": [{"part_name": "文本字段", "part_type": "text_field", "confidence": 0.1, "violation_types": []}]},
        )
        text = report.to_readable_text()
        self.assertIn("自动通过", text)
        self.assertIn("安全知识库", text)

    def test_to_readable_text_pending_manual(self):
        """测试待人工复核决策的 to_readable_text"""
        report = ReviewReport.objects.create(
            content_id=uuid.uuid4(),
            content_type="persona",
            content_name="待审人设卡",
            decision="pending_manual",
            final_confidence=0.65,
            violation_types=["politics"],
            report_data={"parts": []},
        )
        text = report.to_readable_text()
        self.assertIn("待人工复核", text)
        self.assertIn("涉政", text)


class ReviewReportSerializerTest(TestCase):
    """ReviewReportSerializer 序列化器单元测试

    验证序列化输出包含所有必要字段且值正确。
    """

    def setUp(self):
        """测试前准备"""
        self.content_id = uuid.uuid4()
        self.report = ReviewReport.objects.create(
            content_id=self.content_id,
            content_type="knowledge",
            content_name="测试知识库",
            decision="auto_rejected",
            final_confidence=0.92,
            violation_types=["porn", "abuse"],
            report_data={
                "content_name": "测试知识库",
                "content_type": "knowledge",
                "review_time": "2024-01-15T10:30:00Z",
                "decision": "auto_rejected",
                "final_confidence": 0.92,
                "violation_types": ["porn", "abuse"],
                "parts": [],
            },
        )

    def tearDown(self):
        """测试后清理"""
        ReviewReport.objects.all().delete()

    def test_serializer_contains_expected_fields(self):
        """测试序列化输出包含所有预期字段"""
        serializer = ReviewReportSerializer(self.report)
        data = serializer.data
        expected_fields = {
            'id', 'content_id', 'content_type', 'content_name',
            'decision', 'final_confidence', 'violation_types',
            'report_data', 'create_datetime',
        }
        self.assertEqual(set(data.keys()), expected_fields)

    def test_serializer_field_values(self):
        """测试序列化输出的字段值正确"""
        serializer = ReviewReportSerializer(self.report)
        data = serializer.data
        self.assertEqual(data['content_id'], str(self.content_id))
        self.assertEqual(data['content_type'], 'knowledge')
        self.assertEqual(data['content_name'], '测试知识库')
        self.assertEqual(data['decision'], 'auto_rejected')
        self.assertAlmostEqual(data['final_confidence'], 0.92)
        self.assertEqual(data['violation_types'], ['porn', 'abuse'])

    def test_serializer_report_data_preserved(self):
        """测试序列化后 report_data 结构完整保留"""
        serializer = ReviewReportSerializer(self.report)
        data = serializer.data
        self.assertIsInstance(data['report_data'], dict)
        self.assertIn('parts', data['report_data'])
        self.assertEqual(data['report_data']['content_name'], '测试知识库')

    def test_serializer_create_datetime_present(self):
        """测试序列化输出包含 create_datetime"""
        serializer = ReviewReportSerializer(self.report)
        data = serializer.data
        self.assertIsNotNone(data['create_datetime'])

    def test_serializer_id_is_string(self):
        """测试序列化后 id 为字符串格式"""
        serializer = ReviewReportSerializer(self.report)
        data = serializer.data
        self.assertIsInstance(data['id'], str)
        # 验证可以解析回 UUID
        uuid.UUID(data['id'])

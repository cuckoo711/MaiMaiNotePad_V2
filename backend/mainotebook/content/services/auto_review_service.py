"""AI 自动审核服务模块

协调 ModerationService 和 ReviewService 完成自动审核流程。
根据 AI 返回的置信度自动执行通过、拒绝或保持待审核操作。
使用多线程并发调用外部 AI API，提升 IO 密集型审核的吞吐量。
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AutoReviewService:
    """AI 自动审核服务

    协调 ModerationService 和 ReviewService 完成自动审核流程。
    支持知识库和人设卡内容的自动审核，包括文本字段和关联文件。
    """

    # 分段审核最大长度（字符数，128k 上下文模型约可处理 10 万中文字符）
    MAX_SEGMENT_LENGTH = 100000

    # 置信度阈值：低于或等于此值自动通过（放宽到 0.7，即允许一定程度的疑似违规）
    AUTO_APPROVE_THRESHOLD = 0.7

    # 置信度阈值：高于此值自动拒绝（仅限知识库和人设卡，标准较宽松）
    AUTO_REJECT_THRESHOLD = 0.9

    # 并发线程数上限（用于分段审核和多文件审核）
    MAX_WORKERS = 5

    @staticmethod
    def execute_auto_review(content_id: str, content_type: str) -> dict:
        """执行 AI 自动审核主流程

        组装完整审核流程：查找内容 → 创建初始报告 → 拼接文本 → 审核文本字段 → 获取并审核文件
        → 聚合结果 → 执行决策 → 更新报告 → 通知上传者。

        Args:
            content_id: 内容 ID
            content_type: 内容类型（knowledge/persona）

        Returns:
            dict: 审核报告数据，或包含 error 键的错误信息字典
        """
        from mainotebook.content.models import KnowledgeBase, PersonaCard, ReviewReport
        from mainotebook.content.services.moderation_service import (
            get_moderation_service,
        )
        from django.utils import timezone

        # 1. 查找内容对象
        if content_type == "knowledge":
            content = KnowledgeBase.objects.filter(id=content_id).first()
        elif content_type == "persona":
            content = PersonaCard.objects.filter(id=content_id).first()
        else:
            logger.error("无效的内容类型: content_type=%s", content_type)
            return {"error": "无效的内容类型"}

        if content is None:
            logger.error(
                "内容不存在: content_id=%s, content_type=%s",
                content_id, content_type,
            )
            return {"error": "内容不存在"}

        if not content.is_pending:
            logger.warning(
                "内容不在待审核状态: content_id=%s, content_type=%s",
                content_id, content_type,
            )
            return {"error": "内容不在待审核状态"}

        # 2. 创建初始审核报告（状态为 pending_ai）
        report = ReviewReport.objects.create(
            content_id=content_id,
            content_type=content_type,
            content_name=content.name,
            decision="pending_ai",
            final_confidence=0.0,
            violation_types=[],
            report_data={
                "status": "processing",
                "start_time": timezone.now().isoformat(),
                "message": "AI 正在审核中..."
            }
        )

        try:
            moderation_service = get_moderation_service()
            text_type = content_type  # identity 映射

            # 3. 收集所有文本内容（文本字段 + 关联文件）
            all_content_parts = []
            
            # 3.1 文本字段（标题、描述、正文）
            text_fields = AutoReviewService._build_text_fields(content)
            if text_fields:
                all_content_parts.append(f"--- 基础信息 ---\n{text_fields}")

            # 3.2 关联文件内容
            text_files = AutoReviewService._get_text_files(content, content_type)
            for file_obj in text_files:
                file_content = AutoReviewService._read_file_content(file_obj)
                if file_content:
                    file_name = getattr(file_obj, 'file_name', str(file_obj))
                    all_content_parts.append(f"\n\n--- 文件: {file_name} ---\n{file_content}")

            full_content = "\n".join(all_content_parts)

            # 如果没有可审核的内容，直接返回
            if not full_content.strip():
                logger.warning("内容为空，无需审核: content_id=%s", content_id)
                # 更新报告为无内容
                report.decision = "auto_approved"  # 或其他状态
                report.report_data = {"message": "内容为空，自动通过"}
                report.save()
                return {}

            # 4. 对合并后的完整内容进行审核（自动分段）
            # 无论长短，都统一走分段逻辑，长文本会被切分，短文本作为单段处理
            max_confidence, merged_violations, segment_details = (
                AutoReviewService._review_segments(
                    AutoReviewService._split_text_segments(full_content),
                    text_type,
                    source=content_type,
                    content_id=content_id,
                )
            )

            # 5. 构造唯一的聚合结果 Part
            # 从分段详情中收集 flagged_content
            flagged_parts = [
                d.get("flagged_content", "")
                for d in segment_details if d and d.get("flagged_content")
            ]
            
            aggregated_part = {
                "part_name": "完整内容聚合",
                "part_type": "aggregated",
                "confidence": max_confidence,
                "violation_types": merged_violations,
                "decision": "false" if max_confidence > AutoReviewService.AUTO_REJECT_THRESHOLD else (
                    "true" if max_confidence <= AutoReviewService.AUTO_APPROVE_THRESHOLD else "unknown"
                ),
                "segments": segment_details,
                "flagged_content": " | ".join(flagged_parts),
                "raw_output": "",  # 聚合模式下无单一 raw_output
            }

            part_results = [aggregated_part]
            final_confidence = max_confidence
            final_violation_types = merged_violations

            # 6. 执行决策
            try:
                decision = AutoReviewService._make_decision(
                    content_id, content_type,
                    final_confidence, final_violation_types,
                    part_results,
                )
            except Exception as e:
                logger.error(
                    "执行决策失败: content_id=%s, 错误: %s",
                    content_id, e,
                )
                decision = "pending_manual"

            # 7. 更新审核报告
            report_data = {
                "content_name": content.name,
                "content_type": content_type,
                "review_time": timezone.now().isoformat(),
                "decision": decision,
                "final_confidence": final_confidence,
                "violation_types": final_violation_types,
                "parts": part_results,
            }
            
            report.decision = decision
            report.final_confidence = final_confidence
            report.violation_types = final_violation_types
            report.report_data = report_data
            report.save()

            # 8. 通知上传者（可选，这里已经在 _make_decision 后可能触发了 ReviewNotificationService，但原逻辑是在 execute_auto_review 外或 _notify_uploader 中）
            # 原逻辑中有 _notify_uploader 方法，这里应该调用它
            AutoReviewService._notify_uploader(content, content_type, report)

            # 9. 返回报告数据
            return report.report_data

        except Exception as e:
            # API 失败或其他异常，更新报告为错误状态
            logger.error(
                "AI 审核服务异常: content_id=%s, content_type=%s, 错误: %s",
                content_id, content_type, e,
            )
            report.decision = "error"
            report.report_data = {"error": str(e), "message": "AI 审核服务异常"}
            report.save()
            return {"error": "AI 审核服务暂时不可用"}

    @staticmethod
    def _build_text_fields(content) -> str:
        """拼接内容的 name、description、content 字段为审核文本

        将内容对象的 name、description、content 字段用换行符拼接，
        跳过空值字段。

        Args:
            content: 知识库或人设卡模型实例

        Returns:
            str: 拼接后的审核文本
        """
        parts = []
        if content.name:
            parts.append(content.name)
        if content.description:
            parts.append(content.description)
        if content.content:
            parts.append(content.content)
        return "\n".join(parts)

    # 可审核的文件 MIME 类型（纯文本类文件，可直接读取内容）
    REVIEWABLE_MIME_TYPES = [
        'text/plain',           # .txt, 部分 .toml
        'application/json',     # .json
        'application/toml',     # .toml（部分浏览器）
        'text/markdown',        # .md
        'text/x-toml',          # .toml（部分浏览器）
        'application/x-yaml',   # .yaml/.yml
        'text/yaml',            # .yaml/.yml
    ]

    @staticmethod
    def _get_text_files(content, content_type: str) -> List:
        """获取内容关联的可读文本文件列表

        根据 content_type 查询关联的文件，返回所有可以读取文本内容的文件。
        知识库支持 txt、json 文件，人设卡支持 toml 文件。

        Args:
            content: 知识库或人设卡模型实例
            content_type: 内容类型（knowledge/persona）

        Returns:
            list: 可读文本文件对象列表
        """
        from django.db.models import Q

        if content_type not in ('knowledge', 'persona'):
            return []

        # 按 MIME 类型过滤
        mime_q = Q()
        for mime in AutoReviewService.REVIEWABLE_MIME_TYPES:
            mime_q |= Q(file_type=mime)

        # 兜底：按文件扩展名匹配（防止 MIME 类型不准确）
        ext_q = (
            Q(original_name__iendswith='.txt') |
            Q(original_name__iendswith='.json') |
            Q(original_name__iendswith='.toml') |
            Q(original_name__iendswith='.md') |
            Q(original_name__iendswith='.yaml') |
            Q(original_name__iendswith='.yml')
        )

        return list(content.files.filter(mime_q | ext_q))

    @staticmethod
    def _read_file_content(file_obj) -> Optional[str]:
        """安全读取文件内容

        拼接 MEDIA_ROOT 得到绝对路径，以 UTF-8 编码读取文件。
        文件不可读时返回 None 并记录警告日志。

        Args:
            file_obj: 文件模型实例（KnowledgeBaseFile 或 PersonaCardFile）

        Returns:
            Optional[str]: 文件文本内容，不可读时返回 None
        """
        import os
        from django.conf import settings

        try:
            file_path = file_obj.file_path
            # file_path 是相对于 MEDIA_ROOT 的路径，需要拼接
            if not os.path.isabs(file_path):
                file_path = os.path.join(settings.MEDIA_ROOT, file_path)

            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.warning(
                f"文件读取失败，跳过该文件: {file_obj.file_path}, 错误: {e}"
            )
            return None

    @staticmethod
    def _split_text_segments(text: str) -> List[str]:
        """将长文本分段

        优先按段落（\\n\\n）分割，若单段仍超长则按固定长度切分。
        所有分段拼接后等于原始文本。

        Args:
            text: 待分段的文本

        Returns:
            List[str]: 分段后的文本列表
        """
        if len(text) <= AutoReviewService.MAX_SEGMENT_LENGTH:
            return [text]

        max_len = AutoReviewService.MAX_SEGMENT_LENGTH
        # 按段落分割，保留分隔符在前一段末尾
        raw_parts = text.split('\n\n')
        paragraphs = []
        for i, part in enumerate(raw_parts):
            if i < len(raw_parts) - 1:
                # 将分隔符 \n\n 附加到当前段落末尾，确保拼接还原
                paragraphs.append(part + '\n\n')
            else:
                paragraphs.append(part)

        segments = []
        for paragraph in paragraphs:
            if len(paragraph) <= max_len:
                segments.append(paragraph)
            else:
                # 超长段落按固定长度切分
                for i in range(0, len(paragraph), max_len):
                    segments.append(paragraph[i:i + max_len])

        return segments


    @staticmethod
    def _review_segments(
        segments: List[str], text_type: str,
        source: Optional[str] = None,
        content_id: Optional[str] = None,
    ) -> Tuple[float, List[str], List[Dict]]:
        """并发审核多个文本分段

        使用线程池并发调用 ModerationService，显著提升多分段审核速度。

        Args:
            segments: 文本分段列表
            text_type: 文本类型（knowledge/persona）
            source: 审核来源（可选，传递给 moderate）
            content_id: 关联内容 ID（可选，传递给 moderate）

        Returns:
            tuple: (max_confidence, merged_violation_types, segment_details)
                - max_confidence: 所有分段中最高的置信度
                - merged_violation_types: 所有分段违规类型的去重合并列表
                - segment_details: 每段审核详情列表（按原始顺序排列）
        """
        from mainotebook.content.services.moderation_service import (
            get_moderation_service,
        )

        moderation_service = get_moderation_service()

        def _review_one_segment(index_and_segment: Tuple[int, str]) -> Dict:
            """审核单个分段（线程内执行）"""
            index, segment = index_and_segment
            result = moderation_service.moderate(
                segment, text_type,
                source=source,
                content_id=content_id,
            )
            return {
                "segment_index": index + 1,
                "text_summary": segment[:100],
                "confidence": result.get("confidence", 0.0),
                "violation_types": result.get("violation_types", []),
                "decision": result.get("decision", "unknown"),
                "flagged_content": result.get("flagged_content", ""),
                "raw_output": result.get("_meta", {}).get("raw_output", ""),
            }

        # 并发审核所有分段
        workers = min(AutoReviewService.MAX_WORKERS, len(segments))
        segment_details: List[Optional[Dict]] = [None] * len(segments)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {
                executor.submit(_review_one_segment, (i, seg)): i
                for i, seg in enumerate(segments)
            }
            for future in as_completed(future_map):
                idx = future_map[future]
                segment_details[idx] = future.result()

        # 聚合结果
        max_confidence = 0.0
        violation_types_set: set = set()
        for detail in segment_details:
            conf = detail["confidence"]
            if conf > max_confidence:
                max_confidence = conf
            violation_types_set.update(detail["violation_types"])

        return max_confidence, list(violation_types_set), segment_details

    @staticmethod
    def _aggregate_results(results: List[Dict]) -> Tuple[float, List[str]]:
        """综合所有审核结果

        取最高 confidence，合并 violation_types（去重）。

        Args:
            results: 审核结果字典列表，每个包含 'confidence' 和 'violation_types'

        Returns:
            tuple: (max_confidence, merged_violation_types)
                - max_confidence: 所有结果中最高的置信度
                - merged_violation_types: 所有违规类型的去重合并列表
        """
        if not results:
            return 0.0, []

        max_confidence = 0.0
        violation_types_set: set = set()

        for result in results:
            confidence = result.get("confidence", 0.0)
            violations = result.get("violation_types", [])

            if confidence > max_confidence:
                max_confidence = confidence

            violation_types_set.update(violations)

        return max_confidence, list(violation_types_set)

    @staticmethod
    def _make_decision(
        content_id: str,
        content_type: str,
        confidence: float,
        violation_types: List[str],
        part_results: Optional[List[Dict]] = None,
    ) -> str:
        """根据置信度执行审核决策

        - confidence <= 0.7: 自动通过
        - confidence > 0.90: 自动拒绝（知识库/人设卡标准较宽松）
        - 0.7 < confidence <= 0.90: 待人工复核

        Args:
            content_id: 内容 ID
            content_type: 内容类型（knowledge/persona）
            confidence: 最终置信度
            violation_types: 最终违规类型列表
            part_results: 各审核部分的详细结果列表（可选，用于提取违规片段）

        Returns:
            str: 决策结果（auto_approved/auto_rejected/pending_manual）
        """
        from mainotebook.content.services.review_service import ReviewService
        from mainotebook.system.models import Users

        if confidence <= AutoReviewService.AUTO_APPROVE_THRESHOLD:
            # 置信度低于或等于阈值，自动通过
            ai_reviewer, _ = Users.objects.get_or_create(
                username="ai_reviewer",
                defaults={"name": "AI 审核员"},
            )
            try:
                ReviewService.approve_content(content_id, content_type, ai_reviewer)
            except Exception as e:
                logger.error(f"自动通过失败: content_id={content_id}, 错误: {e}")
            return "auto_approved"

        if confidence > AutoReviewService.AUTO_REJECT_THRESHOLD:
            # 置信度高于阈值，自动拒绝
            ai_reviewer, _ = Users.objects.get_or_create(
                username="ai_reviewer",
                defaults={"name": "AI 审核员"},
            )
            # 违规类型英文 → 中文映射
            violation_label_map = {
                'porn': '色情内容',
                'politics': '涉政内容',
                'abuse': '辱骂内容',
                'violence': '暴力内容',
                'spam': '垃圾信息',
                'illegal': '违法内容',
            }
            if violation_types:
                labels = [violation_label_map.get(v, v) for v in violation_types]
                reason = "AI 检测到违规内容：" + "、".join(labels)
            else:
                reason = "AI 检测到违规内容"

            # 从 part_results 中提取违规片段，附加到拒绝原因
            flagged_snippets = AutoReviewService._collect_flagged_content(part_results)
            if flagged_snippets:
                reason += "\n违规片段：" + flagged_snippets

            try:
                ReviewService.reject_content(
                    content_id, content_type, ai_reviewer, reason
                )
            except Exception as e:
                logger.error(f"自动拒绝失败: content_id={content_id}, 错误: {e}")
            return "auto_rejected"

        # 置信度在阈值之间，待人工复核
        return "pending_manual"

    @staticmethod
    def _collect_flagged_content(part_results: Optional[List[Dict]]) -> str:
        """从各审核部分结果中收集违规片段

        Args:
            part_results: 各审核部分的详细结果列表

        Returns:
            str: 合并后的违规片段文本，多个片段用 | 分隔
        """
        if not part_results:
            return ""

        snippets = []
        for part in part_results:
            flagged = part.get("flagged_content", "")
            if flagged and flagged.strip():
                snippets.append(flagged.strip())

            # 也检查分段中的 flagged_content
            for seg in part.get("segments", []):
                seg_flagged = seg.get("flagged_content", "")
                if seg_flagged and seg_flagged.strip():
                    snippets.append(seg_flagged.strip())

        # 去重并合并
        seen = set()
        unique = []
        for s in snippets:
            if s not in seen:
                seen.add(s)
                unique.append(s)

        return " | ".join(unique)


    @staticmethod
    def _generate_report(
        content_id: str,
        content_type: str,
        content_name: str,
        decision: str,
        final_confidence: float,
        final_violation_types: list,
        part_results: list,
    ) -> 'ReviewReport':
        """生成并保存审核报告

        构建包含完整 parts 结构的 report_data，创建 ReviewReport 实例并保存到数据库。

        Args:
            content_id: 内容 ID
            content_type: 内容类型（knowledge/persona）
            content_name: 内容名称
            decision: 审核决策（auto_approved/auto_rejected/pending_manual）
            final_confidence: 最终置信度
            final_violation_types: 最终违规类型列表
            part_results: 各审核部分的详细结果列表

        Returns:
            ReviewReport: 创建并保存的审核报告实例
        """
        from mainotebook.content.models import ReviewReport
        from django.utils import timezone

        # 构建 report_data 结构化数据
        report_data = {
            "content_name": content_name,
            "content_type": content_type,
            "review_time": timezone.now().isoformat(),
            "decision": decision,
            "final_confidence": final_confidence,
            "violation_types": final_violation_types,
            "parts": part_results,
        }

        # 创建并保存审核报告
        report = ReviewReport.objects.create(
            content_id=content_id,
            content_type=content_type,
            content_name=content_name,
            decision=decision,
            final_confidence=final_confidence,
            violation_types=final_violation_types,
            report_data=report_data,
        )

        return report

    @staticmethod
    def _notify_uploader(content, content_type: str, report) -> None:
        """通过站内信通知上传者审核结果

        根据审核决策确定通知类型，调用 ReviewNotificationService 发送站内信和 WebSocket 推送。
        待人工复核的内容不发送通知。通知失败仅记录日志，不影响审核流程。

        Args:
            content: 知识库或人设卡模型实例
            content_type: 内容类型（knowledge/persona）
            report: ReviewReport 审核报告实例
        """
        from mainotebook.content.services.review_notification import (
            ReviewNotificationService,
        )

        # 待人工复核不发送通知
        if report.decision == "pending_manual":
            return

        # 根据决策确定通知动作
        if report.decision == "auto_approved":
            action = "approved"
        else:
            action = "rejected"

        # 构建拒绝原因
        reason = None
        if action == "rejected" and report.violation_types:
            reason = ", ".join(report.violation_types)

        try:
            ReviewNotificationService.send_review_notification(
                uploader_id=content.uploader.id,
                content_name=content.name,
                content_type=content_type,
                action=action,
                reason=reason,
            )
        except Exception as e:
            logger.error(
                "通知上传者失败: content_id=%s, content_type=%s, 错误: %s",
                report.content_id,
                content_type,
                e,
            )


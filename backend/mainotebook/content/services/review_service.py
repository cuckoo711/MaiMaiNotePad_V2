"""
审核服务

提供内容审核相关的业务逻辑。
"""

from typing import Optional, List, Dict
from datetime import timedelta
from django.db.models import Q, Count, Subquery, OuterRef, CharField
from django.core.exceptions import ValidationError
from django.utils import timezone
from mainotebook.system.models import Users
from ..models import KnowledgeBase, PersonaCard, UploadRecord, ReviewReport
from .review_notification import ReviewNotificationService


class ReviewService:
    """审核服务
    
    提供内容审核相关的业务逻辑。
    """
    
    @staticmethod
    def get_pending_items(
        filters: Optional[Dict] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Dict:
        """获取待审核列表（服务端分页）

        使用数据库级过滤、排序和分页，避免内存级操作。
        由于 Django 不支持跨模型 UNION，分别查询两个模型后在 Python 中合并排序分页。

        Args:
            filters: 过滤条件，支持 content_type（内容类型）、search（搜索关键词）
            page: 页码，默认 1
            page_size: 每页数量，默认 10

        Returns:
            dict: 包含 items（待审核项列表）和 total（总数）的字典
        """
        content_type_filter = None
        search_filter = None

        if filters:
            content_type_filter = filters.get('content_type')
            search_filter = filters.get('search')

        items = []

        # 构建搜索条件
        search_q = Q()
        if search_filter:
            search_q = Q(name__icontains=search_filter) | Q(description__icontains=search_filter)

        # 查询待审核的知识库（仅在未指定类型或指定为 knowledge 时查询）
        if not content_type_filter or content_type_filter == 'knowledge':
            kb_qs = KnowledgeBase.objects.filter(
                Q(is_pending=True) & search_q
            ).select_related('uploader').annotate(
                file_count_val=Count('files')
            ).order_by('-create_datetime')

            for kb in kb_qs:
                items.append({
                    'id': kb.id,
                    'name': kb.name,
                    'description': kb.description,
                    'content_type': 'knowledge',
                    'uploader_id': kb.uploader.id,
                    'uploader_name': kb.uploader.name,
                    'create_datetime': kb.create_datetime,
                    'tags': kb.tags,
                    'file_count': kb.file_count_val,
                })

        # 查询待审核的人设卡（仅在未指定类型或指定为 persona 时查询）
        if not content_type_filter or content_type_filter == 'persona':
            pc_qs = PersonaCard.objects.filter(
                Q(is_pending=True) & search_q
            ).select_related('uploader').annotate(
                file_count_val=Count('files')
            ).order_by('-create_datetime')

            for pc in pc_qs:
                items.append({
                    'id': pc.id,
                    'name': pc.name,
                    'description': pc.description,
                    'content_type': 'persona',
                    'uploader_id': pc.uploader.id,
                    'uploader_name': pc.uploader.name,
                    'create_datetime': pc.create_datetime,
                    'tags': pc.tags,
                    'file_count': pc.file_count_val,
                })

        # 合并后按创建时间倒序排序
        items.sort(key=lambda x: x['create_datetime'], reverse=True)

        # 计算总数
        total = len(items)

        # 使用 OFFSET/LIMIT 分页
        offset = (page - 1) * page_size
        items = items[offset:offset + page_size]

        # 批量查询当前页 items 的最新 AI 审核报告
        if items:
            content_ids = [item['id'] for item in items]
            # 查询每个 content_id 的最新报告
            latest_reports = {}
            for report in ReviewReport.objects.filter(
                content_id__in=content_ids
            ).order_by('content_id', '-create_datetime'):
                # 只保留每个 content_id 的第一条（最新）
                if report.content_id not in latest_reports:
                    latest_reports[report.content_id] = report.decision

            # 注入 ai_review_decision 字段
            for item in items:
                item['ai_review_decision'] = latest_reports.get(item['id'], None)

        return {'items': items, 'total': total}
    
    @staticmethod
    def approve_content(
        content_id: str,
        content_type: str,
        reviewer: Users
    ) -> None:
        """批准内容
        
        Args:
            content_id: 内容 ID
            content_type: 内容类型（'knowledge' 或 'persona'）
            reviewer: 审核员
            
        Raises:
            ValidationError: 当内容不存在或状态不正确时
        """
        # 获取内容对象
        if content_type == 'knowledge':
            content = KnowledgeBase.objects.filter(id=content_id).first()
        elif content_type == 'persona':
            content = PersonaCard.objects.filter(id=content_id).first()
        else:
            raise ValidationError("无效的内容类型")
        
        if not content:
            raise ValidationError("内容不存在")
        
        if not content.is_pending:
            raise ValidationError("内容不在待审核状态")
        
        # 更新内容状态
        content.is_pending = False
        content.is_public = True
        content.rejection_reason = None
        content.save()
        
        # 更新上传记录
        UploadRecord.objects.filter(
            target_id=str(content_id),
            target_type=content_type
        ).update(status='approved')
        
        # 发送审核通过通知
        try:
            ReviewNotificationService.send_review_notification(
                uploader_id=content.uploader.id,
                content_name=content.name,
                content_type=content_type,
                action='approved'
            )
        except Exception:
            pass
    
    @staticmethod
    def reject_content(
        content_id: str,
        content_type: str,
        reviewer: Users,
        reason: str
    ) -> None:
        """拒绝内容
        
        Args:
            content_id: 内容 ID
            content_type: 内容类型（'knowledge' 或 'persona'）
            reviewer: 审核员
            reason: 拒绝原因
            
        Raises:
            ValidationError: 当内容不存在或状态不正确时
        """
        if not reason or not reason.strip():
            raise ValidationError("拒绝内容时必须提供原因")
        
        if len(reason) > 500:
            raise ValidationError("拒绝原因不能超过 500 个字符")
        
        # 获取内容对象
        if content_type == 'knowledge':
            content = KnowledgeBase.objects.filter(id=content_id).first()
        elif content_type == 'persona':
            content = PersonaCard.objects.filter(id=content_id).first()
        else:
            raise ValidationError("无效的内容类型")
        
        if not content:
            raise ValidationError("内容不存在")
        
        if not content.is_pending:
            raise ValidationError("内容不在待审核状态")
        
        # 更新内容状态
        content.is_pending = False
        content.is_public = False
        content.rejection_reason = reason
        content.save()
        
        # 更新上传记录
        UploadRecord.objects.filter(
            target_id=str(content_id),
            target_type=content_type
        ).update(status='rejected')
        
        # 发送审核拒绝通知
        try:
            ReviewNotificationService.send_review_notification(
                uploader_id=content.uploader.id,
                content_name=content.name,
                content_type=content_type,
                action='rejected',
                reason=reason
            )
        except Exception:
            pass

    @staticmethod
    def batch_approve(
        ids: List[str],
        content_type: str,
        reviewer: Users
    ) -> Dict:
        """批量审核通过

        逐条调用 approve_content，捕获异常记录失败项。

        Args:
            ids: 内容 ID 列表
            content_type: 内容类型（'knowledge' 或 'persona'）
            reviewer: 审核员

        Returns:
            dict: 包含 success_count（成功数）、fail_count（失败数）、failures（失败详情列表）
        """
        success_count = 0
        fail_count = 0
        failures = []

        for content_id in ids:
            try:
                ReviewService.approve_content(
                    content_id=str(content_id),
                    content_type=content_type,
                    reviewer=reviewer
                )
                success_count += 1
            except Exception as e:
                fail_count += 1
                failures.append({
                    'id': str(content_id),
                    'reason': str(e.message) if hasattr(e, 'message') else str(e)
                })

        return {
            'success_count': success_count,
            'fail_count': fail_count,
            'failures': failures
        }

    @staticmethod
    def batch_reject(
        ids: List[str],
        content_type: str,
        reviewer: Users,
        reason: str
    ) -> Dict:
        """批量审核拒绝

        逐条调用 reject_content，捕获异常记录失败项。

        Args:
            ids: 内容 ID 列表
            content_type: 内容类型（'knowledge' 或 'persona'）
            reviewer: 审核员
            reason: 拒绝原因

        Returns:
            dict: 包含 success_count（成功数）、fail_count（失败数）、failures（失败详情列表）
        """
        success_count = 0
        fail_count = 0
        failures = []

        for content_id in ids:
            try:
                ReviewService.reject_content(
                    content_id=str(content_id),
                    content_type=content_type,
                    reviewer=reviewer,
                    reason=reason
                )
                success_count += 1
            except Exception as e:
                fail_count += 1
                failures.append({
                    'id': str(content_id),
                    'reason': str(e.message) if hasattr(e, 'message') else str(e)
                })

        return {
            'success_count': success_count,
            'fail_count': fail_count,
            'failures': failures
        }


    
    @staticmethod
    def return_content(
        content_id: str,
        content_type: str,
        reviewer: Users,
        reason: str
    ) -> None:
        """退回内容
        
        Args:
            content_id: 内容 ID
            content_type: 内容类型（'knowledge' 或 'persona'）
            reviewer: 审核员
            reason: 退回原因
            
        Raises:
            ValidationError: 当内容不存在或状态不正确时
        """
        # 获取内容对象
        if content_type == 'knowledge':
            content = KnowledgeBase.objects.filter(id=content_id).first()
        elif content_type == 'persona':
            content = PersonaCard.objects.filter(id=content_id).first()
        else:
            raise ValidationError("无效的内容类型")
        
        if not content:
            raise ValidationError("内容不存在")
        
        if not content.is_pending:
            raise ValidationError("内容不在待审核状态")
        
        # 更新内容状态（退回到草稿状态）
        content.is_pending = False
        content.is_public = False
        content.rejection_reason = reason
        content.save()
        
        # 同步更新关联的上传记录状态
        UploadRecord.objects.filter(
            target_id=str(content_id),
            target_type=content_type
        ).update(status='rejected')
    
    @staticmethod
    def get_review_stats() -> Dict:
        """获取审核统计数据
        
        Returns:
            dict: 审核统计数据，包含：
                - pending_count: 待审核总数
                - pending_knowledge: 待审核知识库数
                - pending_persona: 待审核人设卡数
                - approved_today: 今日已批准数
                - rejected_today: 今日已拒绝数
                - pass_rate: 通过率（最近 30 天）
                - ai_takeover_count: AI 接管数（AI 自动通过 + AI 自动拒绝）
        """
        # 待审核数量
        pending_knowledge = KnowledgeBase.objects.filter(
            is_pending=True
        ).count()
        pending_persona = PersonaCard.objects.filter(
            is_pending=True
        ).count()
        
        # 已处理数量（今日）
        today = timezone.now().date()
        approved_today = UploadRecord.objects.filter(
            status='approved',
            update_datetime__date=today
        ).count()
        rejected_today = UploadRecord.objects.filter(
            status='rejected',
            update_datetime__date=today
        ).count()
        
        # 通过率（最近 30 天）
        thirty_days_ago = timezone.now() - timedelta(days=30)
        # 这里计算的是总的通过率，不区分人工还是 AI
        total_reviewed_records = UploadRecord.objects.filter(
            status__in=['approved', 'rejected'],
            update_datetime__gte=thirty_days_ago
        ).count()
        approved_count_records = UploadRecord.objects.filter(
            status='approved',
            update_datetime__gte=thirty_days_ago
        ).count()
        
        pass_rate = (approved_count_records / total_reviewed_records * 100) if total_reviewed_records > 0 else 0
        
        # AI 接管数：AI 审查后直接标记通过或拒绝的数量
        # decision 为 'auto_approved' 或 'auto_rejected'
        ai_takeover_count = ReviewReport.objects.filter(
            decision__in=['auto_approved', 'auto_rejected']
        ).count()
        
        return {
            'pending_count': pending_knowledge + pending_persona,
            'pending_knowledge': pending_knowledge,
            'pending_persona': pending_persona,
            'approved_today': approved_today,
            'rejected_today': rejected_today,
            'pass_rate': round(pass_rate, 2),
            'ai_takeover_count': ai_takeover_count,
        }

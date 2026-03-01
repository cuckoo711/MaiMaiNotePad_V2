"""
审核视图集

提供内容审核功能，仅审核员和管理员可访问。
"""

from rest_framework import viewsets, status as http_status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError

from mainotebook.utils.json_response import DetailResponse, ErrorResponse
from ..permissions import IsModeratorOrAdmin
from ..serializers.review import (
    ReviewItemSerializer,
    ReviewActionSerializer,
    ReviewHistorySerializer,
    BatchReviewSerializer,
    AIReviewRequestSerializer,
    BatchAIReviewRequestSerializer,
    ReviewReportSerializer,
)
from ..models import KnowledgeBase, PersonaCard, ReviewReport
from ..services.review_service import ReviewService
from ..tasks import auto_review_task


class ReviewViewSet(viewsets.ViewSet):
    """审核视图集
    
    提供内容审核功能，仅审核员和管理员可访问。
    包含待审核列表、审核历史、批准、拒绝、退回、统计等功能。
    """
    
    permission_classes = [IsAuthenticated, IsModeratorOrAdmin]
    
    def list(self, request):
        """获取待审核列表（分页）
        
        支持查询参数：
        - content_type: 内容类型（knowledge 或 persona）
        - search: 搜索关键词（在名称和描述中搜索）
        - page: 页码，默认 1
        - page_size: 每页数量，默认 10
        
        Returns:
            Response: 包含分页待审核项列表的响应，格式为 {items, total, page, page_size}
        """
        try:
            # 获取过滤参数
            filters = {}
            content_type = request.query_params.get('content_type')
            search = request.query_params.get('search')
            
            if content_type:
                filters['content_type'] = content_type
            if search:
                filters['search'] = search
            
            # 获取分页参数
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
            
            # 调用服务层获取待审核列表（分页）
            result = ReviewService.get_pending_items(filters, page=page, page_size=page_size)
            
            # 序列化数据
            serializer = ReviewItemSerializer(result['items'], many=True)
            
            return DetailResponse(
                data={
                    'items': serializer.data,
                    'total': result['total'],
                    'page': page,
                    'page_size': page_size,
                },
                msg="获取待审核列表成功"
            )
        except Exception as e:
            return ErrorResponse(
                msg=f"获取待审核列表失败: {str(e)}",
                code=500,
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(methods=['GET'], detail=False)
    def history(self, request):
        """获取审核历史
        
        返回当前审核员处理过的所有审核记录。
        
        Returns:
            Response: 包含审核历史记录的响应
        """
        try:
            # TODO: 实现审核历史查询
            # 当前简化实现，返回空列表
            # 完整实现需要添加审核日志模型来记录审核操作
            
            return DetailResponse(
                data=[],
                msg="获取审核历史成功"
            )
        except Exception as e:
            return ErrorResponse(
                msg=f"获取审核历史失败: {str(e)}",
                code=500,
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(methods=['POST'], detail=True)
    def approve(self, request, pk=None):
        """批准内容
        
        将待审核内容标记为已批准并发布。
        
        Args:
            pk: 内容 ID
            
        Request Body:
            - content_type: 内容类型（knowledge 或 persona）
            - reason: 审核备注（可选）
            
        Returns:
            Response: 批准操作的响应
        """
        try:
            serializer = ReviewActionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            content_type = serializer.validated_data['content_type']
            
            # 调用服务层批准内容
            ReviewService.approve_content(
                content_id=pk,
                content_type=content_type,
                reviewer=request.user
            )
            
            return DetailResponse(
                data=None,
                msg="内容已批准"
            )
        except (DjangoValidationError, ValidationError) as e:
            return ErrorResponse(
                msg=str(e),
                code=400,
                status=http_status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return ErrorResponse(
                msg=f"批准内容失败: {str(e)}",
                code=500,
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(methods=['POST'], detail=True)
    def reject(self, request, pk=None):
        """拒绝内容
        
        将待审核内容标记为已拒绝，并记录拒绝原因。
        
        Args:
            pk: 内容 ID
            
        Request Body:
            - content_type: 内容类型（knowledge 或 persona）
            - reason: 拒绝原因（必填）
            
        Returns:
            Response: 拒绝操作的响应
        """
        try:
            serializer = ReviewActionSerializer(
                data=request.data,
                context={'action': 'reject'}
            )
            serializer.is_valid(raise_exception=True)
            
            content_type = serializer.validated_data['content_type']
            reason = serializer.validated_data.get('reason', '')
            
            # 调用服务层拒绝内容
            ReviewService.reject_content(
                content_id=pk,
                content_type=content_type,
                reviewer=request.user,
                reason=reason
            )
            
            return DetailResponse(
                data=None,
                msg="内容已拒绝"
            )
        except (DjangoValidationError, ValidationError) as e:
            return ErrorResponse(
                msg=str(e),
                code=400,
                status=http_status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return ErrorResponse(
                msg=f"拒绝内容失败: {str(e)}",
                code=500,
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(methods=['POST'], detail=True)
    def return_draft(self, request, pk=None):
        """退回内容
        
        将待审核内容退回到草稿状态，要求用户修改后重新提交。
        
        Args:
            pk: 内容 ID
            
        Request Body:
            - content_type: 内容类型（knowledge 或 persona）
            - reason: 退回原因（可选）
            
        Returns:
            Response: 退回操作的响应
        """
        try:
            serializer = ReviewActionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            content_type = serializer.validated_data['content_type']
            reason = serializer.validated_data.get('reason', '')
            
            # 调用服务层退回内容
            ReviewService.return_content(
                content_id=pk,
                content_type=content_type,
                reviewer=request.user,
                reason=reason
            )
            
            return DetailResponse(
                data=None,
                msg="内容已退回"
            )
        except (DjangoValidationError, ValidationError) as e:
            return ErrorResponse(
                msg=str(e),
                code=400,
                status=http_status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return ErrorResponse(
                msg=f"退回内容失败: {str(e)}",
                code=500,
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(methods=['POST'], detail=False)
    def batch_approve(self, request):
        """批量审核通过
        
        一次性对多条内容执行审核通过操作。
        
        Request Body:
            - ids: 内容 ID 列表
            - content_type: 内容类型（knowledge 或 persona）
            
        Returns:
            Response: 包含 success_count、fail_count、failures 的响应
        """
        try:
            serializer = BatchReviewSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            ids = serializer.validated_data.get('ids', [])
            content_type = serializer.validated_data.get('content_type')
            
            # 校验 ids 不为空
            if not ids:
                return ErrorResponse(
                    msg="请选择要审核的内容",
                    code=400,
                    status=http_status.HTTP_400_BAD_REQUEST
                )
            
            # 校验 content_type 必填
            if not content_type:
                return ErrorResponse(
                    msg="缺少 content_type 参数",
                    code=400,
                    status=http_status.HTTP_400_BAD_REQUEST
                )
            
            # 调用服务层批量审核通过
            result = ReviewService.batch_approve(
                ids=[str(uid) for uid in ids],
                content_type=content_type,
                reviewer=request.user
            )
            
            return DetailResponse(
                data=result,
                msg="批量审核完成"
            )
        except (DjangoValidationError, ValidationError) as e:
            # 处理序列化器验证错误，提取友好消息
            if hasattr(e, 'detail'):
                detail = e.detail
                if isinstance(detail, dict):
                    if 'ids' in detail:
                        return ErrorResponse(
                            msg="请选择要审核的内容",
                            code=400,
                            status=http_status.HTTP_400_BAD_REQUEST
                        )
                    if 'content_type' in detail:
                        return ErrorResponse(
                            msg="缺少 content_type 参数",
                            code=400,
                            status=http_status.HTTP_400_BAD_REQUEST
                        )
            return ErrorResponse(
                msg=str(e),
                code=400,
                status=http_status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return ErrorResponse(
                msg=f"批量审核通过失败: {str(e)}",
                code=500,
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(methods=['POST'], detail=False)
    def batch_reject(self, request):
        """批量审核拒绝
        
        一次性对多条内容执行审核拒绝操作。
        
        Request Body:
            - ids: 内容 ID 列表
            - content_type: 内容类型（knowledge 或 persona）
            - reason: 拒绝原因（必填，最大 500 字符）
            
        Returns:
            Response: 包含 success_count、fail_count、failures 的响应
        """
        try:
            serializer = BatchReviewSerializer(
                data=request.data,
                context={'action': 'batch_reject'}
            )
            serializer.is_valid(raise_exception=True)
            
            ids = serializer.validated_data.get('ids', [])
            content_type = serializer.validated_data.get('content_type')
            reason = serializer.validated_data.get('reason', '')
            
            # 校验 reason 必填且长度不超过 500 字符
            if not reason or not reason.strip():
                return ErrorResponse(
                    msg="拒绝内容时必须提供原因",
                    code=400,
                    status=http_status.HTTP_400_BAD_REQUEST
                )
            
            if len(reason) > 500:
                return ErrorResponse(
                    msg="拒绝原因不能超过 500 个字符",
                    code=400,
                    status=http_status.HTTP_400_BAD_REQUEST
                )
            
            # 调用服务层批量审核拒绝
            result = ReviewService.batch_reject(
                ids=[str(uid) for uid in ids],
                content_type=content_type,
                reviewer=request.user,
                reason=reason
            )
            
            return DetailResponse(
                data=result,
                msg="批量审核完成"
            )
        except (DjangoValidationError, ValidationError) as e:
            # 处理序列化器验证错误，提取友好消息
            if hasattr(e, 'detail'):
                detail = e.detail
                if isinstance(detail, dict):
                    if 'ids' in detail:
                        return ErrorResponse(
                            msg="请选择要审核的内容",
                            code=400,
                            status=http_status.HTTP_400_BAD_REQUEST
                        )
                    if 'content_type' in detail:
                        return ErrorResponse(
                            msg="缺少 content_type 参数",
                            code=400,
                            status=http_status.HTTP_400_BAD_REQUEST
                        )
                    if 'reason' in detail:
                        return ErrorResponse(
                            msg="拒绝内容时必须提供原因",
                            code=400,
                            status=http_status.HTTP_400_BAD_REQUEST
                        )
            return ErrorResponse(
                msg=str(e),
                code=400,
                status=http_status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return ErrorResponse(
                msg=f"批量审核拒绝失败: {str(e)}",
                code=500,
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(methods=['GET'], detail=False)
    def stats(self, request):
        """获取审核统计数据
        
        返回审核相关的统计信息，包括：
        - 待审核总数
        - 待审核知识库数
        - 待审核人设卡数
        - 今日已批准数
        - 今日已拒绝数
        - 通过率（最近 30 天）
        
        Returns:
            Response: 包含统计数据的响应
        """
        try:
            # 调用服务层获取统计数据
            stats = ReviewService.get_review_stats()
            
            return DetailResponse(
                data=stats,
                msg="获取审核统计成功"
            )
        except Exception as e:
            return ErrorResponse(
                msg=f"获取审核统计失败: {str(e)}",
                code=500,
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(methods=['POST'], detail=True)
    def ai_review(self, request, pk=None):
        """单条 AI 审核

        通过 Celery 异步创建 AI 审核任务。

        Args:
            pk: 内容 ID

        Request Body:
            - content_type: 内容类型（knowledge 或 persona）

        Returns:
            Response: 包含 task_id 的响应
        """
        try:
            # 验证请求参数
            serializer = AIReviewRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            content_type = serializer.validated_data['content_type']

            # 根据内容类型查询内容
            if content_type == 'knowledge':
                content = KnowledgeBase.objects.filter(id=pk).first()
            elif content_type == 'persona':
                content = PersonaCard.objects.filter(id=pk).first()
            else:
                return ErrorResponse(
                    msg="无效的 content_type",
                    code=400,
                    status=http_status.HTTP_400_BAD_REQUEST
                )

            # 检查内容是否存在
            if not content:
                return ErrorResponse(
                    msg="内容不存在",
                    code=400,
                    status=http_status.HTTP_400_BAD_REQUEST
                )

            # 检查内容是否在待审核状态
            if not content.is_pending:
                return ErrorResponse(
                    msg="内容不在待审核状态",
                    code=400,
                    status=http_status.HTTP_400_BAD_REQUEST
                )

            # 检查是否有正在进行中的 AI 审核（2 分钟内已创建过报告）
            from django.utils import timezone
            from datetime import timedelta
            recent_cutoff = timezone.now() - timedelta(minutes=2)
            recent_report = ReviewReport.objects.filter(
                content_id=pk,
                content_type=content_type,
                create_datetime__gte=recent_cutoff,
            ).exists()
            if recent_report:
                return ErrorResponse(
                    msg="该内容的 AI 审核正在进行中或刚刚完成，请稍后再试",
                    code=409,
                    status=http_status.HTTP_409_CONFLICT
                )

            # 调度 Celery 异步任务
            task_result = auto_review_task.delay(str(pk), content_type)

            return DetailResponse(
                data={"task_id": task_result.id},
                msg="AI 审核任务已创建"
            )
        except (DjangoValidationError, ValidationError) as e:
            return ErrorResponse(
                msg=str(e),
                code=400,
                status=http_status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return ErrorResponse(
                msg=f"AI 审核失败: {str(e)}",
                code=500,
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(methods=['POST'], detail=False)
    def batch_ai_review(self, request):
        """批量 AI 审核

        为每条内容分别创建 Celery 异步任务。

        Request Body:
            - ids: 内容 ID 列表
            - content_type: 内容类型（knowledge 或 persona）

        Returns:
            Response: 包含 total 和 task_ids 的响应
        """
        try:
            # 验证请求参数
            serializer = BatchAIReviewRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            ids = serializer.validated_data['ids']
            content_type = serializer.validated_data['content_type']

            # 校验 ids 不为空
            if not ids:
                return ErrorResponse(
                    msg="请选择要审核的内容",
                    code=400,
                    status=http_status.HTTP_400_BAD_REQUEST
                )

            # 为每条内容创建独立的异步任务
            task_ids = []
            for content_id in ids:
                task_result = auto_review_task.delay(str(content_id), content_type)
                task_ids.append(task_result.id)

            return DetailResponse(
                data={"total": len(ids), "task_ids": task_ids},
                msg="批量 AI 审核任务已创建"
            )
        except (DjangoValidationError, ValidationError) as e:
            return ErrorResponse(
                msg=str(e),
                code=400,
                status=http_status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return ErrorResponse(
                msg=f"批量 AI 审核失败: {str(e)}",
                code=500,
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(methods=['GET'], detail=True)
    def ai_report(self, request, pk=None):
        """查看 AI 审核报告

        返回指定内容的最新 ReviewReport。

        Args:
            pk: 内容 ID

        Query Params:
            - content_type: 内容类型（knowledge 或 persona）

        Returns:
            Response: 包含审核报告详情的响应
        """
        try:
            # 验证 content_type 参数
            content_type = request.query_params.get('content_type')
            if not content_type:
                return ErrorResponse(
                    msg="缺少 content_type 参数",
                    code=400,
                    status=http_status.HTTP_400_BAD_REQUEST
                )

            # 查询最新的审核报告
            report = ReviewReport.objects.filter(
                content_id=pk, content_type=content_type
            ).order_by('-create_datetime').first()

            if not report:
                return ErrorResponse(
                    msg="未找到审核报告",
                    code=400,
                    status=http_status.HTTP_400_BAD_REQUEST
                )

            # 序列化报告数据
            serializer = ReviewReportSerializer(report)
            return DetailResponse(
                data=serializer.data,
                msg="获取审核报告成功"
            )
        except Exception as e:
            return ErrorResponse(
                msg=f"获取审核报告失败: {str(e)}",
                code=500,
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
            )


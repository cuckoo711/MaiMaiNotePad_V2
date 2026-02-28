# -*- coding: utf-8 -*-

"""
用户扩展视图集

提供用户数据统计和历史查询功能，包括上传历史、统计数据、概览信息和活动趋势。
"""

from datetime import datetime, timedelta
from django.db.models import Count, Q
from django.utils import timezone
from django.shortcuts import redirect
from django.http import Http404
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from mainotebook.utils.json_response import DetailResponse, ErrorResponse
from mainotebook.system.models import Users
from mainotebook.content.models import (
    KnowledgeBase,
    PersonaCard,
    UploadRecord,
    StarRecord,
    Comment
)


class UserExtensionViewSet(viewsets.ViewSet):
    """用户扩展视图集
    
    提供用户数据统计和历史查询功能。
    
    操作：
    - uploads: 获取用户上传历史
    - stats: 获取用户上传统计
    - overview: 获取用户数据概览
    - trend: 获取用户活动趋势
    """
    
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_summary='获取用户上传历史',
        operation_description='返回当前用户创建的所有内容（知识库和人设卡）及其状态',
        manual_parameters=[
            openapi.Parameter(
                'content_type',
                openapi.IN_QUERY,
                description='内容类型筛选（可选）：knowledge（知识库）或 persona（人设卡）',
                type=openapi.TYPE_STRING,
                required=False,
                enum=['knowledge', 'persona']
            ),
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description='状态筛选（可选）：pending（待审核）、approved（已通过）、rejected（已拒绝）',
                type=openapi.TYPE_STRING,
                required=False,
                enum=['pending', 'approved', 'rejected']
            )
        ],
        responses={
            200: openapi.Response(
                description='上传历史列表',
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_STRING, description='内容ID'),
                            'name': openapi.Schema(type=openapi.TYPE_STRING, description='内容名称'),
                            'description': openapi.Schema(type=openapi.TYPE_STRING, description='内容描述'),
                            'content_type': openapi.Schema(type=openapi.TYPE_STRING, description='内容类型'),
                            'status': openapi.Schema(type=openapi.TYPE_STRING, description='审核状态'),
                            'is_public': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='是否公开'),
                            'star_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='收藏数'),
                            'downloads': openapi.Schema(type=openapi.TYPE_INTEGER, description='下载数'),
                            'create_datetime': openapi.Schema(type=openapi.TYPE_STRING, description='创建时间'),
                            'rejection_reason': openapi.Schema(type=openapi.TYPE_STRING, description='拒绝原因'),
                        }
                    )
                )
            ),
            400: '参数错误'
        }
    )
    @action(methods=['GET'], detail=False)
    def uploads(self, request):
        """获取用户上传历史
        
        Args:
            request: HTTP 请求对象
            
        Query Parameters:
            content_type (str, optional): 内容类型筛选，可选值：'knowledge'、'persona'
            status (str, optional): 状态筛选，可选值：'pending'、'approved'、'rejected'
            
        Returns:
            Response: 包含上传历史列表的响应
        """
        # 获取查询参数
        content_type = request.query_params.get('content_type', None)
        status_filter = request.query_params.get('status', None)
        
        # 验证参数
        if content_type and content_type not in ['knowledge', 'persona']:
            return ErrorResponse(
                msg="无效的内容类型，可选值：knowledge、persona",
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if status_filter and status_filter not in ['pending', 'approved', 'rejected']:
            return ErrorResponse(
                msg="无效的状态，可选值：pending、approved、rejected",
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            uploads = []
            
            # 获取知识库
            if not content_type or content_type == 'knowledge':
                knowledge_bases = KnowledgeBase.objects.filter(
                    uploader=request.user
                )
                
                for kb in knowledge_bases:
                    # 确定状态
                    if kb.is_pending:
                        item_status = 'pending'
                    elif kb.is_public:
                        item_status = 'approved'
                    else:
                        item_status = 'rejected' if kb.rejection_reason else 'pending'
                    
                    # 应用状态筛选
                    if status_filter and item_status != status_filter:
                        continue
                    
                    uploads.append({
                        'id': str(kb.id),
                        'name': kb.name,
                        'description': kb.description,
                        'content_type': 'knowledge',
                        'status': item_status,
                        'is_public': kb.is_public,
                        'star_count': kb.star_count,
                        'downloads': kb.downloads,
                        'create_datetime': kb.create_datetime.isoformat(),
                        'rejection_reason': kb.rejection_reason
                    })
            
            # 获取人设卡
            if not content_type or content_type == 'persona':
                persona_cards = PersonaCard.objects.filter(
                    uploader=request.user
                )
                
                for pc in persona_cards:
                    # 确定状态
                    if pc.is_pending:
                        item_status = 'pending'
                    elif pc.is_public:
                        item_status = 'approved'
                    else:
                        item_status = 'rejected' if pc.rejection_reason else 'pending'
                    
                    # 应用状态筛选
                    if status_filter and item_status != status_filter:
                        continue
                    
                    uploads.append({
                        'id': str(pc.id),
                        'name': pc.name,
                        'description': pc.description,
                        'content_type': 'persona',
                        'status': item_status,
                        'is_public': pc.is_public,
                        'star_count': pc.star_count,
                        'downloads': pc.downloads,
                        'create_datetime': pc.create_datetime.isoformat(),
                        'rejection_reason': pc.rejection_reason
                    })
            
            # 按创建时间倒序排序
            uploads.sort(key=lambda x: x['create_datetime'], reverse=True)
            
            return DetailResponse(data=uploads, msg="获取成功")
            
        except Exception as e:
            return ErrorResponse(
                msg=f"获取上传历史失败: {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_summary='获取用户上传统计',
        operation_description='返回当前用户按类型和状态分组的统计数据',
        responses={
            200: openapi.Response(
                description='上传统计数据',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total': openapi.Schema(type=openapi.TYPE_INTEGER, description='总上传数'),
                        'knowledge': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'total': openapi.Schema(type=openapi.TYPE_INTEGER, description='知识库总数'),
                                'pending': openapi.Schema(type=openapi.TYPE_INTEGER, description='待审核数'),
                                'approved': openapi.Schema(type=openapi.TYPE_INTEGER, description='已通过数'),
                                'rejected': openapi.Schema(type=openapi.TYPE_INTEGER, description='已拒绝数'),
                            }
                        ),
                        'persona': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'total': openapi.Schema(type=openapi.TYPE_INTEGER, description='人设卡总数'),
                                'pending': openapi.Schema(type=openapi.TYPE_INTEGER, description='待审核数'),
                                'approved': openapi.Schema(type=openapi.TYPE_INTEGER, description='已通过数'),
                                'rejected': openapi.Schema(type=openapi.TYPE_INTEGER, description='已拒绝数'),
                            }
                        ),
                        'pass_rate': openapi.Schema(type=openapi.TYPE_NUMBER, description='通过率（百分比）'),
                    }
                )
            )
        }
    )
    @action(methods=['GET'], detail=False)
    def stats(self, request):
        """获取用户上传统计
        
        Args:
            request: HTTP 请求对象
            
        Returns:
            Response: 包含上传统计数据的响应
        """
        try:
            # 知识库统计
            kb_total = KnowledgeBase.objects.filter(
                uploader=request.user
            ).count()
            
            kb_pending = KnowledgeBase.objects.filter(
                uploader=request.user,
                is_pending=True
            ).count()
            
            kb_approved = KnowledgeBase.objects.filter(
                uploader=request.user,
                is_public=True,
                is_pending=False
            ).count()
            
            kb_rejected = KnowledgeBase.objects.filter(
                uploader=request.user,
                is_public=False,
                is_pending=False,
                rejection_reason__isnull=False
            ).count()
            
            # 人设卡统计
            pc_total = PersonaCard.objects.filter(
                uploader=request.user
            ).count()
            
            pc_pending = PersonaCard.objects.filter(
                uploader=request.user,
                is_pending=True
            ).count()
            
            pc_approved = PersonaCard.objects.filter(
                uploader=request.user,
                is_public=True,
                is_pending=False
            ).count()
            
            pc_rejected = PersonaCard.objects.filter(
                uploader=request.user,
                is_public=False,
                is_pending=False,
                rejection_reason__isnull=False
            ).count()
            
            # 计算总数和通过率
            total = kb_total + pc_total
            total_approved = kb_approved + pc_approved
            total_submitted = total - kb_pending - pc_pending  # 已提交审核的数量
            
            pass_rate = (total_approved / total_submitted * 100) if total_submitted > 0 else 0
            
            stats_data = {
                'total': total,
                'knowledge': {
                    'total': kb_total,
                    'pending': kb_pending,
                    'approved': kb_approved,
                    'rejected': kb_rejected
                },
                'persona': {
                    'total': pc_total,
                    'pending': pc_pending,
                    'approved': pc_approved,
                    'rejected': pc_rejected
                },
                'pass_rate': round(pass_rate, 2)
            }
            
            return DetailResponse(data=stats_data, msg="获取成功")
            
        except Exception as e:
            return ErrorResponse(
                msg=f"获取上传统计失败: {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_summary='获取用户数据概览',
        operation_description='返回用户的关键指标（上传数、收藏数、评论数、获赞数）',
        responses={
            200: openapi.Response(
                description='用户数据概览',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'upload_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='上传数'),
                        'star_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='收藏数'),
                        'comment_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='评论数'),
                        'like_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='获赞数'),
                        'content_star_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='内容被收藏数'),
                    }
                )
            )
        }
    )
    @action(methods=['GET'], detail=False)
    def overview(self, request):
        """获取用户数据概览
        
        Args:
            request: HTTP 请求对象
            
        Returns:
            Response: 包含用户数据概览的响应
        """
        try:
            # 上传数（知识库 + 人设卡）
            upload_count = (
                KnowledgeBase.objects.filter(
                    uploader=request.user
                ).count() +
                PersonaCard.objects.filter(
                    uploader=request.user
                ).count()
            )
            
            # 收藏数（用户收藏的内容数量）
            star_count = StarRecord.objects.filter(user=request.user).count()
            
            # 评论数（用户发表的评论数量）
            comment_count = Comment.objects.filter(
                user=request.user
            ).count()
            
            # 获赞数（用户评论获得的点赞总数）
            like_count = Comment.objects.filter(
                user=request.user
            ).aggregate(total_likes=Count('like_count'))['total_likes'] or 0
            
            # 内容被收藏数（用户上传的内容被收藏的总数）
            kb_ids = KnowledgeBase.objects.filter(
                uploader=request.user
            ).values_list('id', flat=True)
            
            pc_ids = PersonaCard.objects.filter(
                uploader=request.user
            ).values_list('id', flat=True)
            
            content_star_count = StarRecord.objects.filter(
                Q(target_id__in=[str(id) for id in kb_ids], target_type='knowledge') |
                Q(target_id__in=[str(id) for id in pc_ids], target_type='persona')
            ).count()
            
            overview_data = {
                'upload_count': upload_count,
                'star_count': star_count,
                'comment_count': comment_count,
                'like_count': like_count,
                'content_star_count': content_star_count
            }
            
            return DetailResponse(data=overview_data, msg="获取成功")
            
        except Exception as e:
            return ErrorResponse(
                msg=f"获取数据概览失败: {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_summary='获取用户活动趋势',
        operation_description='返回指定时间范围内的活动趋势数据（按日/周/月聚合）',
        manual_parameters=[
            openapi.Parameter(
                'period',
                openapi.IN_QUERY,
                description='时间周期：day（按日）、week（按周）、month（按月），默认为 day',
                type=openapi.TYPE_STRING,
                required=False,
                enum=['day', 'week', 'month']
            ),
            openapi.Parameter(
                'days',
                openapi.IN_QUERY,
                description='查询天数，默认为 30 天',
                type=openapi.TYPE_INTEGER,
                required=False
            )
        ],
        responses={
            200: openapi.Response(
                description='活动趋势数据',
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'date': openapi.Schema(type=openapi.TYPE_STRING, description='日期'),
                            'upload_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='上传数'),
                            'comment_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='评论数'),
                            'star_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='收藏数'),
                        }
                    )
                )
            ),
            400: '参数错误'
        }
    )
    @action(methods=['GET'], detail=False)
    def trend(self, request):
        """获取用户活动趋势
        
        Args:
            request: HTTP 请求对象
            
        Query Parameters:
            period (str, optional): 时间周期，可选值：'day'、'week'、'month'，默认为 'day'
            days (int, optional): 查询天数，默认为 30 天
            
        Returns:
            Response: 包含活动趋势数据的响应
        """
        # 获取查询参数
        period = request.query_params.get('period', 'day')
        try:
            days = int(request.query_params.get('days', 30))
        except ValueError:
            return ErrorResponse(
                msg="无效的天数参数",
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 验证参数
        if period not in ['day', 'week', 'month']:
            return ErrorResponse(
                msg="无效的时间周期，可选值：day、week、month",
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if days < 1 or days > 365:
            return ErrorResponse(
                msg="天数必须在 1-365 之间",
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 计算起始日期
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            # 初始化趋势数据
            trend_data = []
            
            # 根据周期生成日期列表
            if period == 'day':
                current_date = start_date.date()
                while current_date <= end_date.date():
                    # 统计当天的活动
                    day_start = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
                    day_end = timezone.make_aware(datetime.combine(current_date, datetime.max.time()))
                    
                    upload_count = (
                        KnowledgeBase.objects.filter(
                            uploader=request.user,
                            create_datetime__gte=day_start,
                            create_datetime__lte=day_end
                        ).count() +
                        PersonaCard.objects.filter(
                            uploader=request.user,
                            create_datetime__gte=day_start,
                            create_datetime__lte=day_end
                        ).count()
                    )
                    
                    comment_count = Comment.objects.filter(
                        user=request.user,
                        create_datetime__gte=day_start,
                        create_datetime__lte=day_end
                    ).count()
                    
                    star_count = StarRecord.objects.filter(
                        user=request.user,
                        create_datetime__gte=day_start,
                        create_datetime__lte=day_end
                    ).count()
                    
                    trend_data.append({
                        'date': current_date.isoformat(),
                        'upload_count': upload_count,
                        'comment_count': comment_count,
                        'star_count': star_count
                    })
                    
                    current_date += timedelta(days=1)
            
            elif period == 'week':
                # 按周聚合（简化实现：每 7 天为一周）
                current_date = start_date.date()
                while current_date <= end_date.date():
                    week_end = min(current_date + timedelta(days=6), end_date.date())
                    
                    week_start = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
                    week_end_dt = timezone.make_aware(datetime.combine(week_end, datetime.max.time()))
                    
                    upload_count = (
                        KnowledgeBase.objects.filter(
                            uploader=request.user,
                            create_datetime__gte=week_start,
                            create_datetime__lte=week_end_dt
                        ).count() +
                        PersonaCard.objects.filter(
                            uploader=request.user,
                            create_datetime__gte=week_start,
                            create_datetime__lte=week_end_dt
                        ).count()
                    )
                    
                    comment_count = Comment.objects.filter(
                        user=request.user,
                        create_datetime__gte=week_start,
                        create_datetime__lte=week_end_dt
                    ).count()
                    
                    star_count = StarRecord.objects.filter(
                        user=request.user,
                        create_datetime__gte=week_start,
                        create_datetime__lte=week_end_dt
                    ).count()
                    
                    trend_data.append({
                        'date': f"{current_date.isoformat()} ~ {week_end.isoformat()}",
                        'upload_count': upload_count,
                        'comment_count': comment_count,
                        'star_count': star_count
                    })
                    
                    current_date += timedelta(days=7)
            
            elif period == 'month':
                # 按月聚合
                current_date = start_date.date()
                while current_date <= end_date.date():
                    # 获取当月的第一天和最后一天
                    month_start = current_date.replace(day=1)
                    if month_start.month == 12:
                        month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
                    else:
                        month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
                    
                    month_end = min(month_end, end_date.date())
                    
                    month_start_dt = timezone.make_aware(datetime.combine(month_start, datetime.min.time()))
                    month_end_dt = timezone.make_aware(datetime.combine(month_end, datetime.max.time()))
                    
                    upload_count = (
                        KnowledgeBase.objects.filter(
                            uploader=request.user,
                            create_datetime__gte=month_start_dt,
                            create_datetime__lte=month_end_dt
                        ).count() +
                        PersonaCard.objects.filter(
                            uploader=request.user,
                            create_datetime__gte=month_start_dt,
                            create_datetime__lte=month_end_dt
                        ).count()
                    )
                    
                    comment_count = Comment.objects.filter(
                        user=request.user,
                        create_datetime__gte=month_start_dt,
                        create_datetime__lte=month_end_dt
                    ).count()
                    
                    star_count = StarRecord.objects.filter(
                        user=request.user,
                        create_datetime__gte=month_start_dt,
                        create_datetime__lte=month_end_dt
                    ).count()
                    
                    trend_data.append({
                        'date': month_start.strftime('%Y-%m'),
                        'upload_count': upload_count,
                        'comment_count': comment_count,
                        'star_count': star_count
                    })
                    
                    # 移动到下个月
                    if month_start.month == 12:
                        current_date = month_start.replace(year=month_start.year + 1, month=1, day=1)
                    else:
                        current_date = month_start.replace(month=month_start.month + 1, day=1)
            
            return DetailResponse(data=trend_data, msg="获取成功")
            
        except Exception as e:
            return ErrorResponse(
                msg=f"获取活动趋势失败: {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_summary='获取用户收藏列表',
        operation_description='返回当前用户收藏的所有内容（知识库和人设卡），支持按类型筛选',
        manual_parameters=[
            openapi.Parameter(
                'target_type',
                openapi.IN_QUERY,
                description='目标类型筛选（可选）：knowledge（知识库）或 persona（人设卡）',
                type=openapi.TYPE_STRING,
                required=False,
                enum=['knowledge', 'persona']
            )
        ],
        responses={
            200: '收藏列表',
            400: '参数错误'
        }
    )
    @action(methods=['GET'], detail=False, url_path='stars')
    def stars(self, request):
        """获取用户收藏列表
        
        Args:
            request: HTTP 请求对象
            
        Query Parameters:
            target_type (str, optional): 目标类型筛选，可选值：'knowledge'、'persona'
            
        Returns:
            Response: 包含收藏列表的响应
        """
        # 获取查询参数
        target_type = request.query_params.get('target_type', None)
        
        # 验证 target_type 参数
        if target_type and target_type not in ['knowledge', 'persona']:
            return ErrorResponse(
                msg="无效的目标类型，可选值：knowledge、persona",
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 导入序列化器
            from mainotebook.content.serializers.star import StarRecordSerializer
            from mainotebook.content.services.star_service import StarService
            
            # 调用服务层获取收藏列表
            queryset = StarService.get_user_stars(request.user, target_type)
            
            # 序列化数据
            serializer = StarRecordSerializer(
                queryset,
                many=True,
                context={'request': request}
            )
            
            return DetailResponse(data=serializer.data, msg="获取成功")
            
        except Exception as e:
            return ErrorResponse(
                msg=f"获取收藏列表失败: {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_summary='获取用户收藏统计',
        operation_description='返回当前用户的收藏统计数据，包含总数和按类型分组的数量',
        responses={
            200: openapi.Response(
                description='收藏统计数据',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total': openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            description='总收藏数'
                        ),
                        'knowledge': openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            description='知识库收藏数'
                        ),
                        'persona': openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            description='人设卡收藏数'
                        )
                    }
                )
            )
        }
    )
    @action(methods=['GET'], detail=False, url_path='stars/stats')
    def stars_stats(self, request):
        """获取用户收藏统计
        
        Args:
            request: HTTP 请求对象
            
        Returns:
            Response: 包含收藏统计数据的响应
        """
        try:
            # 导入服务
            from mainotebook.content.services.star_service import StarService
            
            # 调用服务层获取统计数据
            stats_data = StarService.get_star_stats(request.user)
            
            return DetailResponse(data=stats_data, msg="获取成功")
            
        except Exception as e:
            return ErrorResponse(
                msg=f"获取收藏统计失败: {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny], url_path='avatar')
    def avatar(self, request, pk=None):
        """获取用户头像（公开访问）
        
        Args:
            request: HTTP 请求对象
            pk: 用户ID
            
        Returns:
            Response: 重定向到头像文件或返回404
        """
        try:
            user = Users.objects.get(pk=pk)
            if user.avatar:
                # 如果是完整URL（http/https开头），直接重定向
                if user.avatar.startswith('http'):
                    return redirect(user.avatar)
                # 如果已经是完整路径（/media/开头），直接重定向
                if user.avatar.startswith('/media/'):
                    return redirect(user.avatar)
                # 如果是相对路径，拼接MEDIA_URL
                avatar_url = f"{settings.MEDIA_URL}{user.avatar}".replace('//', '/')
                return redirect(avatar_url)
            else:
                # 用户没有头像
                raise Http404("User has no avatar")
        except Users.DoesNotExist:
            raise Http404("User not found")
        except Exception as e:
            return ErrorResponse(
                msg=f"获取头像失败: {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

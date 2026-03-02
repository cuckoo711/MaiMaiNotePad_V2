# -*- coding: utf-8 -*-
"""首页统计数据视图

提供面向普通用户的首页统计信息，包括：
- 平台总体数据（知识库数量、人设卡数量、用户数量）
- 个人数据（我的上传、我的下载、我的评论）
- 热门内容（热门知识库、热门人设卡）
- 最新动态（最新知识库、最新人设卡）
"""

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from mainotebook.utils.json_response import DetailResponse
from mainotebook.utils.viewset import CustomModelViewSet
from mainotebook.content.models import (
    KnowledgeBase, PersonaCard, UploadRecord, 
    DownloadRecord, Comment
)
from mainotebook.system.models import Users


class HomeStatsViewSet(CustomModelViewSet):
    """首页统计数据视图集
    
    提供首页所需的各类统计数据
    """
    
    queryset = Users.objects.none()  # 不需要实际的 queryset
    permission_classes = [AllowAny]  # 首页数据允许所有人访问
    
    @action(methods=['GET'], detail=False, permission_classes=[AllowAny])
    def platform_stats(self, request):
        """获取平台总体统计数据
        
        Returns:
            - total_knowledge: 知识库总数
            - total_persona: 人设卡总数
            - total_users: 用户总数
            - total_downloads: 总下载次数
        """
        # 统计公开的知识库和人设卡
        total_knowledge = KnowledgeBase.objects.filter(
            is_public=True
        ).count()
        
        total_persona = PersonaCard.objects.filter(
            is_public=True
        ).count()
        
        total_users = Users.objects.filter(
            is_active=True
        ).count()
        
        total_downloads = DownloadRecord.objects.count()
        
        return DetailResponse(data={
            'total_knowledge': total_knowledge,
            'total_persona': total_persona,
            'total_users': total_users,
            'total_downloads': total_downloads,
        })
    
    @action(methods=['GET'], detail=False, permission_classes=[IsAuthenticated])
    def my_stats(self, request):
        """获取当前用户的个人统计数据
        
        Returns:
            - my_uploads: 我的上传数
            - my_downloads: 我的下载数
            - my_comments: 我的评论数
            - my_pending: 我的待审核数
        """
        user = request.user
        
        # 我的上传数（知识库 + 人设卡）
        my_knowledge = KnowledgeBase.objects.filter(uploader=user).count()
        my_persona = PersonaCard.objects.filter(uploader=user).count()
        my_uploads = my_knowledge + my_persona
        
        # 我的下载数
        my_downloads = DownloadRecord.objects.filter(creator=user).count()
        
        # 我的评论数
        my_comments = Comment.objects.filter(user=user).count()
        
        # 我的待审核数
        my_pending = UploadRecord.objects.filter(
            uploader=user,
            status='pending'
        ).count()
        
        return DetailResponse(data={
            'my_uploads': my_uploads,
            'my_downloads': my_downloads,
            'my_comments': my_comments,
            'my_pending': my_pending,
        })
    
    @action(methods=['GET'], detail=False, permission_classes=[AllowAny])
    def hot_content(self, request):
        """获取热门内容（按下载量排序）
        
        Returns:
            - hot_knowledge: 热门知识库列表（前5）
            - hot_persona: 热门人设卡列表（前5）
        """
        # 热门知识库（按 downloads 字段排序）
        hot_knowledge = KnowledgeBase.objects.filter(
            is_public=True
        ).order_by('-downloads')[:5].values(
            'id', 'name', 'description', 'downloads'
        )
        
        # 热门人设卡（按 downloads 字段排序）
        hot_persona = PersonaCard.objects.filter(
            is_public=True
        ).order_by('-downloads')[:5].values(
            'id', 'name', 'description', 'downloads'
        )
        
        # 重命名字段以保持前端兼容
        hot_knowledge_list = [
            {
                'id': str(item['id']),
                'name': item['name'],
                'description': item['description'],
                'download_count': item['downloads']
            }
            for item in hot_knowledge
        ]
        
        hot_persona_list = [
            {
                'id': str(item['id']),
                'name': item['name'],
                'description': item['description'],
                'download_count': item['downloads']
            }
            for item in hot_persona
        ]
        
        return DetailResponse(data={
            'hot_knowledge': hot_knowledge_list,
            'hot_persona': hot_persona_list,
        })
    
    @action(methods=['GET'], detail=False, permission_classes=[AllowAny])
    def recent_content(self, request):
        """获取最新内容
        
        Returns:
            - recent_knowledge: 最新知识库列表（前5）
            - recent_persona: 最新人设卡列表（前5）
        """
        # 最新知识库
        recent_knowledge = KnowledgeBase.objects.filter(
            is_public=True
        ).order_by('-create_datetime')[:5].values(
            'id', 'name', 'description', 'create_datetime'
        )
        
        # 最新人设卡
        recent_persona = PersonaCard.objects.filter(
            is_public=True
        ).order_by('-create_datetime')[:5].values(
            'id', 'name', 'description', 'create_datetime'
        )
        
        return DetailResponse(data={
            'recent_knowledge': list(recent_knowledge),
            'recent_persona': list(recent_persona),
        })
    
    @action(methods=['GET'], detail=False, permission_classes=[AllowAny])
    def monthly_trend(self, request):
        """获取月度趋势数据（最近12个月）
        
        Returns:
            - months: 月份列表
            - knowledge_counts: 知识库上传数量
            - persona_counts: 人设卡上传数量
        """
        now = timezone.now()
        months = []
        knowledge_counts = []
        persona_counts = []
        
        for i in range(11, -1, -1):
            # 计算月份
            month_start = (now - timedelta(days=30*i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if i == 0:
                month_end = now
            else:
                month_end = (now - timedelta(days=30*(i-1))).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # 月份标签
            months.append(f"{month_start.month}月")
            
            # 统计该月的知识库数量
            knowledge_count = KnowledgeBase.objects.filter(
                create_datetime__gte=month_start,
                create_datetime__lt=month_end
            ).count()
            knowledge_counts.append(knowledge_count)
            
            # 统计该月的人设卡数量
            persona_count = PersonaCard.objects.filter(
                create_datetime__gte=month_start,
                create_datetime__lt=month_end
            ).count()
            persona_counts.append(persona_count)
        
        return DetailResponse(data={
            'months': months,
            'knowledge_counts': knowledge_counts,
            'persona_counts': persona_counts,
        })

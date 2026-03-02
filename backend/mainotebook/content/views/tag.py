# -*- coding: utf-8 -*-

"""
标签视图集

提供热门标签查询和标签统计功能。
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from mainotebook.utils.json_response import DetailResponse, ErrorResponse
from mainotebook.content.services.tag_service import TagService

import logging

logger = logging.getLogger(__name__)


class TagViewSet(viewsets.ViewSet):
    """标签视图集
    
    提供标签相关的查询和管理功能。
    
    自定义操作：
    - popular: 获取热门标签列表（公开访问）
    - rebuild: 重建标签统计数据（管理员）
    - clear_cache: 清除标签缓存（管理员）
    """
    
    # 默认不需要认证
    permission_classes = []
    
    @swagger_auto_schema(
        operation_summary='获取热门标签',
        operation_description='返回热门标签列表，按热度分数排序',
        manual_parameters=[
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description='返回的标签数量，默认20个',
                type=openapi.TYPE_INTEGER,
                default=20
            ),
            openapi.Parameter(
                'tag_type',
                openapi.IN_QUERY,
                description='标签类型：knowledge-知识库，persona-人设卡，默认knowledge',
                type=openapi.TYPE_STRING,
                default='knowledge'
            )
        ],
        responses={
            200: openapi.Response(
                description='热门标签列表',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='状态码'),
                        'msg': openapi.Schema(type=openapi.TYPE_STRING, description='消息'),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'tag': openapi.Schema(type=openapi.TYPE_STRING, description='标签名称'),
                                    'usage_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='使用次数'),
                                    'search_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='搜索次数'),
                                    'hot_score': openapi.Schema(type=openapi.TYPE_NUMBER, description='热度分数'),
                                }
                            )
                        )
                    }
                )
            )
        }
    )
    @action(methods=['GET'], detail=False)
    def popular(self, request):
        """获取热门标签列表
        
        Args:
            request: HTTP 请求对象
            
        Returns:
            Response: 包含热门标签列表的响应
        """
        try:
            limit = int(request.query_params.get('limit', 20))
            if limit <= 0 or limit > 100:
                limit = 20
        except (ValueError, TypeError):
            limit = 20
        
        # 获取标签类型参数
        tag_type = request.query_params.get('tag_type', 'knowledge')
        if tag_type not in ['knowledge', 'persona']:
            tag_type = 'knowledge'
        
        try:
            tags = TagService.get_popular_tags(limit=limit, tag_type=tag_type)
            return DetailResponse(data=tags, msg="获取成功")
        except Exception as e:
            logger.error(f"获取热门标签失败: {e}")
            return ErrorResponse(msg="获取热门标签失败", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_summary='重建标签统计',
        operation_description='扫描所有知识库和人设卡，重新统计标签使用次数（管理员）',
        responses={
            200: openapi.Response(
                description='重建成功',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='状态码'),
                        'msg': openapi.Schema(type=openapi.TYPE_STRING, description='消息'),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'total_tags': openapi.Schema(type=openapi.TYPE_INTEGER, description='标签总数'),
                                'total_usage': openapi.Schema(type=openapi.TYPE_INTEGER, description='总使用次数'),
                            }
                        )
                    }
                )
            ),
            403: '无权限操作'
        }
    )
    @action(methods=['POST'], detail=False, permission_classes=[IsAdminUser])
    def rebuild(self, request):
        """重建标签统计数据
        
        扫描所有知识库和人设卡，重新统计标签使用次数。
        仅管理员可操作。
        
        Args:
            request: HTTP 请求对象
            
        Returns:
            Response: 重建结果响应
        """
        try:
            result = TagService.rebuild_statistics()
            logger.info(f"管理员 {request.user.id} 重建标签统计: {result}")
            return DetailResponse(data=result, msg="重建成功")
        except Exception as e:
            logger.error(f"重建标签统计失败: {e}")
            return ErrorResponse(msg=f"重建失败: {str(e)}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_summary='清除标签缓存',
        operation_description='清除热门标签缓存，下次查询时重新生成（管理员）',
        responses={
            200: '清除成功',
            403: '无权限操作'
        }
    )
    @action(methods=['POST'], detail=False, permission_classes=[IsAdminUser])
    def clear_cache(self, request):
        """清除标签缓存
        
        清除热门标签缓存，下次查询时重新生成。
        仅管理员可操作。
        
        Args:
            request: HTTP 请求对象
            
        Returns:
            Response: 清除结果响应
        """
        try:
            TagService.clear_cache()
            logger.info(f"管理员 {request.user.id} 清除标签缓存")
            return DetailResponse(data=[], msg="清除成功")
        except Exception as e:
            logger.error(f"清除标签缓存失败: {e}")
            return ErrorResponse(msg=f"清除失败: {str(e)}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# -*- coding: utf-8 -*-

"""
收藏视图集

提供用户收藏管理功能，包括收藏列表查询和统计。
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from mainotebook.utils.json_response import DetailResponse, ErrorResponse
from mainotebook.content.serializers.star import StarRecordSerializer
from mainotebook.content.services.star_service import StarService


class StarViewSet(viewsets.ViewSet):
    """收藏视图集
    
    提供用户收藏管理功能。
    
    注意：收藏和取消收藏功能已在知识库和人设卡 ViewSet 中实现（star、unstar action）。
    本 ViewSet 主要提供收藏列表查询和统计功能。
    
    操作：
    - list: 获取用户收藏列表（支持按类型筛选）
    - stats: 获取用户收藏统计
    """
    
    permission_classes = [IsAuthenticated]
    
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
            200: StarRecordSerializer(many=True),
            400: '参数错误'
        }
    )
    def list(self, request):
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
    @action(methods=['GET'], detail=False)
    def stats(self, request):
        """获取用户收藏统计
        
        Args:
            request: HTTP 请求对象
            
        Returns:
            Response: 包含收藏统计数据的响应
        """
        try:
            # 调用服务层获取统计数据
            stats_data = StarService.get_star_stats(request.user)
            
            return DetailResponse(data=stats_data, msg="获取成功")
            
        except Exception as e:
            return ErrorResponse(
                msg=f"获取收藏统计失败: {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

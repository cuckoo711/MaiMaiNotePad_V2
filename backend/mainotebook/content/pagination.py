# -*- coding: utf-8 -*-

"""
分页配置模块

提供与 FastAPI 应用兼容的分页格式。
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """标准分页配置
    
    与 FastAPI 应用保持一致的分页格式。
    
    分页参数：
        - page: 页码（默认 1）
        - page_size: 每页数量（默认 20，最大 100）
    
    响应格式：
        {
            "count": 总记录数,
            "next": 下一页 URL,
            "previous": 上一页 URL,
            "results": 结果列表
        }
    """
    
    # 默认每页数量
    page_size = 20
    
    # 页码查询参数名
    page_query_param = 'page'
    
    # 每页数量查询参数名
    page_size_query_param = 'page_size'
    
    # 最大每页数量
    max_page_size = 100
    
    def get_paginated_response(self, data):
        """返回分页响应
        
        Args:
            data: 序列化后的数据列表
            
        Returns:
            Response: DRF 响应对象，包含分页信息和数据
        """
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })

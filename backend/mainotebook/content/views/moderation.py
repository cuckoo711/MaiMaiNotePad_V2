"""
AI 内容审核视图
"""

import logging

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..serializers.moderation import (
    ModerationRequestSerializer,
    ModerationResponseSerializer,
)
from ..services.moderation_service import get_moderation_service

logger = logging.getLogger(__name__)


@api_view(['POST'])
def check_content(request):
    """内容审核接口
    
    对用户提交的文本进行 AI 审核，判断是否包含违规内容（色情、涉政、辱骂）。
    
    Args:
        request: HTTP 请求对象，包含待审核文本和文本类型
        
    Returns:
        Response: 审核结果，包含决策、置信度和违规类型
    """
    # 验证请求数据
    request_serializer = ModerationRequestSerializer(data=request.data)
    if not request_serializer.is_valid():
        return Response(
            {
                'success': False,
                'message': '请求参数错误',
                'errors': request_serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        text = request_serializer.validated_data['text']
        text_type = request_serializer.validated_data.get('text_type', 'comment')
        
        logger.info(f"收到审核请求 - 文本类型: {text_type}, 文本长度: {len(text)}")
        
        # 获取审核服务并执行审核
        service = get_moderation_service()
        result = service.moderate(text=text, text_type=text_type)
        
        # 构建响应
        response_data = {
            'success': True,
            'result': result,
            'message': '审核完成'
        }
        
        response_serializer = ModerationResponseSerializer(data=response_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            logger.error(f"响应序列化失败: {response_serializer.errors}")
            return Response(response_data, status=status.HTTP_200_OK)
    
    except ValueError as e:
        logger.error(f"审核服务配置错误: {e}")
        return Response(
            {
                'success': False,
                'message': f'审核服务配置错误: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    except Exception as e:
        logger.error(f"审核过程发生异常: {e}", exc_info=True)
        return Response(
            {
                'success': False,
                'message': f'审核失败: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def health_check(request):
    """审核服务健康检查
    
    检查审核服务是否正常运行。
    
    Returns:
        Response: 服务状态信息
    """
    try:
        service = get_moderation_service()
        return Response(
            {
                'success': True,
                'data': {
                    'status': 'healthy',
                    'model': service.model,
                    'base_url': service.base_url
                },
                'message': '服务正常'
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return Response(
            {
                'success': False,
                'message': f'服务异常: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

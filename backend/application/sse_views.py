# views.py
import time
import logging

import jwt
from django.http import StreamingHttpResponse

from application import settings
from mainotebook.system.models import MessageCenterTargetUser
from django.core.cache import cache

logger = logging.getLogger(__name__)


def event_stream(user_id):
    """SSE 事件流生成器
    
    Args:
        user_id: 用户 ID
        
    Yields:
        str: SSE 格式的消息
    """
    last_sent_time = 0
    connection_start = time.time()
    max_connection_time = 3600  # 最大连接时间 1 小时
    heartbeat_interval = 30  # 心跳间隔 30 秒
    last_heartbeat = time.time()

    try:
        while True:
            current_time = time.time()
            
            # 检查连接是否超时
            if current_time - connection_start > max_connection_time:
                logger.info(f"SSE 连接超时，用户 {user_id}")
                break
            
            # 发送心跳保持连接
            if current_time - last_heartbeat > heartbeat_interval:
                yield ": heartbeat\n\n"
                last_heartbeat = current_time
            
            # 从 Redis 中获取最后数据库变更时间
            last_db_change_time = cache.get('last_db_change_time', 0)
            
            # 只有当数据库发生变化时才检查总数
            if last_db_change_time and last_db_change_time > last_sent_time:
                count = MessageCenterTargetUser.objects.filter(
                    users=user_id, 
                    is_read=False
                ).count()
                yield f"data: {count}\n\n"
                last_sent_time = current_time

            time.sleep(1)
            
    except GeneratorExit:
        # 客户端断开连接
        logger.debug(f"SSE 连接关闭，用户 {user_id}")
    except Exception as e:
        logger.error(f"SSE 连接异常，用户 {user_id}: {e}")


def sse_view(request):
    """SSE 视图
    
    Args:
        request: HTTP 请求对象
        
    Returns:
        StreamingHttpResponse: SSE 响应
    """
    token = request.GET.get('token')
    if not token:
        return StreamingHttpResponse(status=401)
        
    try:
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        user_id = decoded.get('user_id')
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return StreamingHttpResponse(status=401)

    response = StreamingHttpResponse(
        event_stream(user_id), 
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # 禁用 nginx 缓冲
    return response

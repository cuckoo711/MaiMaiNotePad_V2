"""
视图层模块

提供 RESTful API 视图集，处理 HTTP 请求和响应。
"""

from .knowledge_base import KnowledgeBaseViewSet
from .persona_card import PersonaCardViewSet
from .comment import CommentViewSet
from .review import ReviewViewSet
from .star import StarViewSet
from .user_extension import UserExtensionViewSet
from .admin_extension import AdminExtensionViewSet
from .moderation_log import ModerationLogViewSet
from .ai_model import AIModelViewSet

__all__ = [
    'KnowledgeBaseViewSet',
    'PersonaCardViewSet',
    'CommentViewSet',
    'ReviewViewSet',
    'StarViewSet',
    'UserExtensionViewSet',
    'AdminExtensionViewSet',
    'ModerationLogViewSet',
    'AIModelViewSet',
]

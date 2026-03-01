"""
Content 应用 URL 配置

定义内容相关的 API 路由，保持与 FastAPI 应用的 URL 路径一致。

路由映射：
- /api/content/knowledge/ -> 知识库管理
- /api/content/persona/ -> 人设卡管理
- /api/content/comments/ -> 评论系统
- /api/content/review/ -> 内容审核
- /api/content/moderation/ -> AI 内容审核
- /api/content/users/ -> 用户扩展功能
- /api/content/admin/users/ -> 管理员扩展功能
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from mainotebook.content.views import (
    KnowledgeBaseViewSet,
    PersonaCardViewSet,
    CommentViewSet,
    ReviewViewSet,
    StarViewSet,
    UserExtensionViewSet,
    AdminExtensionViewSet,
    ModerationLogViewSet,
    AIModelViewSet,
)
from mainotebook.content.views.moderation import check_content, health_check

# 创建路由器
# 使用 DefaultRouter 以获得 API 根视图和格式后缀支持
router = DefaultRouter()

# 注册知识库视图集
# FastAPI 路径: /api/knowledge/*
# Django 路径: /api/content/knowledge/*
# 提供的端点：
# - GET /api/content/knowledge/ - 获取公开知识库列表
# - POST /api/content/knowledge/ - 创建知识库
# - GET /api/content/knowledge/{id}/ - 获取知识库详情
# - PUT /api/content/knowledge/{id}/ - 更新知识库
# - DELETE /api/content/knowledge/{id}/ - 删除知识库
# - GET /api/content/knowledge/my/ - 获取个人知识库列表
# - POST /api/content/knowledge/{id}/files/ - 添加文件
# - DELETE /api/content/knowledge/{id}/files/{file_id}/ - 删除文件
# - GET /api/content/knowledge/{id}/files/{file_id}/ - 下载文件
# - POST /api/content/knowledge/{id}/submit/ - 提交审核
# - POST /api/content/knowledge/{id}/star/ - 收藏
# - DELETE /api/content/knowledge/{id}/star/ - 取消收藏
router.register(r'knowledge', KnowledgeBaseViewSet, basename='knowledge')

# 注册人设卡视图集
# FastAPI 路径: /api/persona/*
# Django 路径: /api/content/persona/*
# 提供的端点：
# - GET /api/content/persona/ - 获取公开人设卡列表
# - POST /api/content/persona/ - 创建人设卡
# - GET /api/content/persona/{id}/ - 获取人设卡详情
# - PUT /api/content/persona/{id}/ - 更新人设卡
# - DELETE /api/content/persona/{id}/ - 删除人设卡
# - GET /api/content/persona/my/ - 获取个人人设卡列表
# - POST /api/content/persona/{id}/files/ - 添加文件
# - DELETE /api/content/persona/{id}/files/{file_id}/ - 删除文件
# - GET /api/content/persona/{id}/files/{file_id}/ - 下载文件
# - POST /api/content/persona/{id}/submit/ - 提交审核
# - POST /api/content/persona/{id}/star/ - 收藏
# - DELETE /api/content/persona/{id}/star/ - 取消收藏
router.register(r'persona', PersonaCardViewSet, basename='persona')

# 注册评论视图集
# FastAPI 路径: /api/comments/*
# Django 路径: /api/content/comments/*
# 提供的端点：
# - GET /api/content/comments/ - 获取评论列表（支持树形结构）
# - POST /api/content/comments/ - 发表评论
# - DELETE /api/content/comments/{id}/ - 删除评论
# - POST /api/content/comments/{id}/like/ - 点赞评论
# - DELETE /api/content/comments/{id}/like/ - 取消点赞
# - POST /api/content/comments/{id}/restore/ - 恢复评论（管理员）
router.register(r'comments', CommentViewSet, basename='comment')

# 注册审核视图集
# FastAPI 路径: /api/review/*
# Django 路径: /api/content/review/*
# 提供的端点：
# - GET /api/content/review/pending/ - 获取待审核列表
# - GET /api/content/review/history/ - 获取审核历史
# - GET /api/content/review/stats/ - 获取审核统计
# - POST /api/content/review/{id}/approve/ - 批准内容
# - POST /api/content/review/{id}/reject/ - 拒绝内容
# - POST /api/content/review/{id}/return/ - 退回内容
router.register(r'review', ReviewViewSet, basename='review')

# 注册用户扩展视图集
# FastAPI 路径: /api/users/*
# Django 路径: /api/content/users/*
# 提供的端点：
# - GET /api/content/users/uploads/ - 获取上传历史
# - GET /api/content/users/stats/ - 获取上传统计
# - GET /api/content/users/overview/ - 获取数据概览
# - GET /api/content/users/trend/ - 获取数据趋势
# - GET /api/content/users/stars/ - 获取收藏列表（StarViewSet 的功能）
router.register(r'users', UserExtensionViewSet, basename='user-extension')

# 注册管理员扩展视图集
# FastAPI 路径: /api/admin/users/*
# Django 路径: /api/content/admin/users/*
# 提供的端点：
# - POST /api/content/admin/users/{id}/mute/ - 禁言用户
# - POST /api/content/admin/users/{id}/ban/ - 封禁用户
# - POST /api/content/admin/users/{id}/unban/ - 解封用户
# - PUT /api/content/admin/users/{id}/role/ - 修改用户角色
# - GET /api/content/admin/users/{id}/status/ - 获取用户状态
router.register(r'admin/users', AdminExtensionViewSet, basename='admin-extension')

# 注册 AI 审核日志视图集
# Django 路径: /api/content/moderation-logs/*
# 提供的端点：
# - GET /api/content/moderation-logs/ - 获取审核日志列表
# - GET /api/content/moderation-logs/{id}/ - 获取审核日志详情
# - GET /api/content/moderation-logs/stats/ - 获取审核统计数据
router.register(r'moderation-logs', ModerationLogViewSet, basename='moderation-log')

# 注册 AI 审核模型管理视图集
# Django 路径: /api/content/ai-models/*
# 提供的端点：
# - GET /api/content/ai-models/ - 获取模型列表
# - POST /api/content/ai-models/ - 新增模型
# - GET /api/content/ai-models/{id}/ - 获取模型详情
# - PUT /api/content/ai-models/{id}/ - 更新模型
# - DELETE /api/content/ai-models/{id}/ - 删除模型
router.register(r'ai-models', AIModelViewSet, basename='ai-model')

# URL 模式
# 注意：路由器会自动生成标准的 REST 端点
# 自定义 action 通过 @action 装饰器在 ViewSet 中定义
urlpatterns = [
    # AI 内容审核端点
    # FastAPI 路径: /api/moderation/check
    # Django 路径: /api/content/moderation/check/
    path('moderation/check/', check_content, name='moderation-check'),
    
    # AI 审核服务健康检查
    # FastAPI 路径: /api/moderation/health
    # Django 路径: /api/content/moderation/health/
    path('moderation/health/', health_check, name='moderation-health'),
] + router.urls

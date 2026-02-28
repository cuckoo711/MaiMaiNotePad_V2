"""内容管理模块常量定义

本模块定义了内容管理相关的常量，包括：
- 内容类型
- 审核状态
- 反应类型
- 文件类型和大小限制
- 评论长度限制
- 错误消息
"""

# 内容类型
CONTENT_TYPE_KNOWLEDGE = 'knowledge'
CONTENT_TYPE_PERSONA = 'persona'

CONTENT_TYPES = [
    (CONTENT_TYPE_KNOWLEDGE, '知识库'),
    (CONTENT_TYPE_PERSONA, '人设卡'),
]

# 审核状态
STATUS_PENDING = 'pending'
STATUS_APPROVED = 'approved'
STATUS_REJECTED = 'rejected'

REVIEW_STATUSES = [
    (STATUS_PENDING, '待审核'),
    (STATUS_APPROVED, '已通过'),
    (STATUS_REJECTED, '已拒绝'),
]

# 反应类型
REACTION_LIKE = 'like'
REACTION_DISLIKE = 'dislike'

REACTION_TYPES = [
    (REACTION_LIKE, '点赞'),
    (REACTION_DISLIKE, '点踩'),
]

# 文件类型
ALLOWED_IMAGE_TYPES = ['jpg', 'jpeg', 'png', 'gif', 'webp']
ALLOWED_DOCUMENT_TYPES = ['pdf', 'txt', 'md']
ALLOWED_CONFIG_TYPES = ['toml', 'json', 'yaml', 'yml']

ALL_ALLOWED_TYPES = ALLOWED_IMAGE_TYPES + ALLOWED_DOCUMENT_TYPES + ALLOWED_CONFIG_TYPES

# 文件大小限制（字节）
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# 评论长度限制
MAX_COMMENT_LENGTH = 500

# 错误消息
ERROR_MESSAGES = {
    'permission_denied': '您没有权限执行此操作',
    'resource_not_found': '请求的资源不存在',
    'duplicate_name': '您已经创建了同名的内容',
    'duplicate_star': '您已经收藏过该内容',
    'duplicate_submit': '内容已处于待审核状态',
    'invalid_file_type': '不支持的文件类型',
    'file_too_large': '文件大小超过限制',
    'comment_too_long': '评论内容不能超过 500 字符',
    'comment_empty': '评论内容不能为空',
    'user_muted': '您已被禁言，无法发表评论',
    'toml_missing': '人设卡必须包含 bot_config.toml 文件',
    'toml_multiple': '人设卡只能包含一个 bot_config.toml 文件',
    'toml_invalid': 'TOML 文件格式错误',
}

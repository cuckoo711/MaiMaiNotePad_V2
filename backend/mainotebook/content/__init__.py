"""
Content 应用初始化模块

该应用包含从 FastAPI 项目迁移过来的内容相关模型，包括：
- 知识库（KnowledgeBase）
- 人设卡（PersonaCard）
- 评论系统（Comment）
- 收藏记录（StarRecord）
- 上传下载记录（UploadRecord, DownloadRecord）
- 邮箱验证（EmailVerification）
"""

default_app_config = 'mainotebook.content.apps.ContentConfig'

# 麦麦笔记本 MaiMaiNotePad

内容管理与分享平台，支持知识库和人设卡的创建、分享、收藏、评论，以及 AI 自动内容审核。

## 项目结构

```
├── backend/        # Django 后端服务
├── admin_web/      # 管理后台前端（Vue 3 + Element Plus + Fast-Crud）
└── mai_f_old/      # 用户前端（Vue 3 + Element Plus）
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Django 4.2 + DRF 3.15 + PostgreSQL + Redis + Celery |
| 管理后台 | Vue 3 + TypeScript + Element Plus + Fast-Crud + Vite 5 |
| 用户前端 | Vue 3 + Element Plus + Vite 7 |
| 实时通信 | Django Channels + WebSocket |
| 认证 | JWT（`JWT` 前缀） |
| API 文档 | Swagger / ReDoc（drf-yasg） |

## 核心功能

- 知识库 / 人设卡的 CRUD、文件上传下载、公开广场浏览
- 树形评论系统（回复、点赞/点踩）
- 收藏系统
- 内容审核：AI 自动审核（Celery 异步） + 管理员人工审核
- 用户系统：邮箱验证注册、RBAC 权限（超级管理员 / 管理员 / 审核员 / 普通用户）
- 站内消息 + WebSocket 实时推送
- 管理后台：内容管理、用户管理（封禁/禁言）、数据统计看板

## 快速开始

### 一键启动后端

```bash
# 首次启动（自动创建环境、安装依赖、启动 Docker、迁移数据库、初始化数据）
bash start_backend.sh --init

# 日常启动
bash start_backend.sh

# 全量重置后启动
bash start_backend.sh --reset
```

脚本会自动完成：环境检测 → Conda 环境创建/激活 → 依赖安装 → Docker 服务启动 → 数据库迁移 → 启动服务。

### Celery 异步任务

```bash
# 前台启动 Worker + Beat（Ctrl+C 停止）
bash start_celery.sh

# 查看运行状态
bash start_celery.sh status

# 实时查看日志
bash start_celery.sh logs

# 停止 / 重启
bash start_celery.sh stop
bash start_celery.sh restart
```

### 手动启动后端

```bash
conda activate mai_notebook
cd backend
pip install -r requirements.txt
docker-compose up -d
cp conf/env.example.py conf/env.py  # 首次需要，编辑填写配置
python manage.py makemigrations
python manage.py migrate
python manage.py init -y            # 首次需要
python main.py
```

### 管理后台前端

```bash
# 开发模式（默认，端口 8060）
bash start_admin_web.sh

# 生产构建
bash start_admin_web.sh --build

# 开发环境构建
bash start_admin_web.sh --build-dev
```

### 用户前端

```bash
# 开发模式（默认，端口 5173）
bash start_user_web.sh

# 生产构建
bash start_user_web.sh --build

# 构建后预览
bash start_user_web.sh --preview
```

## 默认账号

| 账号 | 密码 | 角色 |
|------|------|------|
| superadmin | admin123456 | 超级管理员 |
| admin | admin123456 | 管理员 |

## 文档

详细文档见各子项目：

- [后端文档](backend/README.md)（含 API 路由、架构说明、部署指南）
- [后端功能文档索引](backend/docs/README.md)（认证、内容管理、审核、WebSocket、Celery 等）
- [管理后台文档](admin_web/README.md)
- [用户前端文档](mai_f_old/README.md)

## 许可证

MIT

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

## 核心功能

- 知识库 / 人设卡管理：CRUD、文件上传下载、公开广场浏览
- 社区互动：树形评论、收藏、点赞/点踩
- 内容审核：AI 自动审核 + 管理员人工审核
- 用户系统：邮箱验证注册、RBAC 权限管理
- 实时通信：站内消息 + WebSocket 推送
- 管理后台：内容管理、用户管理、数据统计

## 快速开始

### 后端服务

```bash
# 首次启动（自动创建环境、安装依赖、启动 Docker、迁移数据库、初始化数据）
bash start_backend.sh --init

# 日常启动
bash start_backend.sh

# 启动 Celery 异步任务（另开终端）
bash start_celery.sh
```

### 前端服务

```bash
# 管理后台（端口 8060）
bash start_admin_web.sh

# 用户前端（端口 5173）
bash start_user_web.sh
```

## 默认账号

| 账号 | 密码 | 角色 |
|------|------|------|
| superadmin | admin123456 | 超级管理员 |
| admin | admin123456 | 管理员 |

## 文档

- [后端文档](backend/README.md) - API 路由、架构说明、部署指南
- [后端功能文档](backend/docs/README.md) - 认证、内容管理、审核、WebSocket、Celery 等
- [管理后台文档](admin_web/README.md)
- [用户前端文档](mai_f_old/README.md)

## 许可证

MIT

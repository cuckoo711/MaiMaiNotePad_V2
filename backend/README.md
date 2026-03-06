# 麦麦笔记本 · 后端服务

基于 Django + Django REST Framework 构建的内容管理与分享平台后端服务，提供知识库、人设卡、评论、收藏、内容审核等功能的 RESTful API。

## 技术栈

| 类别 | 技术 |
|------|------|
| Web 框架 | Django 4.2 + Django REST Framework 3.15 |
| 数据库 | PostgreSQL |
| 缓存 / 消息队列 | Redis |
| 异步任务 | Celery + django-celery-beat |
| 实时通信 | Django Channels + WebSocket |
| 认证 | JWT（`JWT` 前缀） |
| API 文档 | Swagger / ReDoc |
| 服务器 | Gunicorn / Uvicorn |

## 项目结构

```
backend/
├── application/            # Django 项目配置
│   ├── settings.py         # 主配置文件
│   ├── urls.py             # 根路由
│   ├── asgi.py / wsgi.py   # ASGI/WSGI 入口
│   ├── celery.py           # Celery 配置
│   └── websocketConfig.py  # WebSocket 消费者
├── conf/                   # 环境配置
│   ├── env.py              # 当前环境配置（需手动创建）
│   └── env.example.py      # 配置模板
├── mainotebook/            # 业务代码
│   ├── system/             # 系统管理（用户、角色、权限、消息）
│   ├── content/            # 内容管理（知识库、人设卡、评论、收藏、审核）
│   └── utils/              # 公共工具（基类、过滤器、中间件、权限）
├── docs/                   # 项目文档
│   ├── 功能文档/           # 功能说明
│   ├── 技术文档/           # 技术实现
│   ├── 开发文档/           # 开发指南
│   └── archive/            # 归档文档
├── scripts/                # 运维脚本
├── tests/                  # 测试代码
├── manage.py               # Django CLI
├── main.py                 # Uvicorn 启动
├── docker-compose.yml      # Docker 编排
└── requirements.txt        # Python 依赖
```

## 快速开始

### 前置依赖

- Python 3.11+（推荐使用 Conda）
- Docker（PostgreSQL + Redis）

### 一键启动

```bash
# 首次启动（自动创建环境、安装依赖、启动服务、初始化数据）
bash ../start_backend.sh --init

# 日常启动
bash ../start_backend.sh

# 启动 Celery 异步任务（另开终端）
bash ../start_celery.sh
```

### 手动启动

```bash
# 1. 创建并激活环境
conda create -n mai_notebook python=3.11
conda activate mai_notebook

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动 Docker 服务
docker-compose up -d

# 4. 配置环境（首次）
cp conf/env.example.py conf/env.py
# 编辑 conf/env.py，填写数据库、Redis、邮件 SMTP、AI API Key 等配置

# 5. 数据库迁移与初始化
python manage.py makemigrations
python manage.py migrate
python manage.py init -y

# 6. 启动服务
python main.py
```

服务启动后访问：
- Swagger 文档：http://localhost:8000/
- ReDoc 文档：http://localhost:8000/redoc/

### 全量重置

```bash
# 清库 + 重建 + 初始化
python scripts/full_reset.py

# 包含测试用户
python scripts/full_reset.py --test
```

## 核心功能

详细文档见 [文档索引](docs/README.md)。

### 系统管理

- 用户管理：邮箱验证注册、JWT 认证、RBAC 权限
- 消息中心：站内消息 + WebSocket 实时推送
- 系统配置：键值对配置、操作日志

### 内容管理

- 知识库 / 人设卡：CRUD、文件管理、审核流程
- 评论系统：树形评论、点赞/点踩
- 收藏系统：内容收藏
- 内容审核：AI 自动审核 + 人工审核

### 异步任务

- AI 自动审核（Celery）
- 批量审核任务
- 定时任务调度

## 默认账号

| 账号 | 密码 | 角色 |
|------|------|------|
| superadmin | admin123456 | 超级管理员 |
| admin | admin123456 | 管理员 |

## API 路由

| 路径 | 说明 |
|------|------|
| `/api/system/` | 用户、角色、部门、菜单、配置、日志 |
| `/api/content/knowledge/` | 知识库 CRUD、文件管理、审核、收藏 |
| `/api/content/persona/` | 人设卡 CRUD、文件管理、审核、收藏 |
| `/api/content/comments/` | 评论、回复、点赞 |
| `/api/content/review/` | 内容审核、批量审核 |
| `/api/register/` | 邮箱注册、验证 |
| `/api/token/` | JWT 登录、刷新 |
| `ws/<service_uid>/` | WebSocket 实时推送 |

## 测试

```bash
pytest                              # 运行所有测试
pytest mainotebook/content/tests/   # 运行指定模块
```

## 生产部署

```bash
# Uvicorn（推荐，支持 WebSocket）
uvicorn application.asgi:application --host 0.0.0.0 --port 8000 --workers 4

# Gunicorn（仅 HTTP）
gunicorn application.wsgi:application -c gunicorn_conf.py
```

## 开发注意事项

- `conf/env.py` 包含敏感配置，需手动创建（参考 `env.example.py`）
- 所有模型使用 UUID 主键
- Auth header 使用 `JWT` 前缀（不是 `Bearer`）
- 公开内容提交时自动触发 AI 审核（Celery 异步）
- 前台 ViewSet 需设置 `extra_filter_class = []` 禁用数据权限过滤

# 麦麦笔记本 · 后端服务

麦麦笔记本（MaiMaiNotePad）是一个内容管理与分享平台的后端服务，基于 Django + Django REST Framework 构建，提供用户管理、知识库、人设卡、评论、收藏、内容审核等功能的 RESTful API。

## 技术栈

| 类别 | 技术 |
|------|------|
| Web 框架 | Django 4.2 + Django REST Framework 3.15 |
| 数据库 | PostgreSQL |
| 缓存 / 消息队列 | Redis（业务缓存 DB 1 + Celery Broker DB 3） |
| 异步任务 | Celery（通过 dvadmin3-celery 集成） |
| 实时通信 | Django Channels + channels-redis（WebSocket） |
| 认证 | JWT（djangorestframework-simplejwt），使用 `JWT` 前缀 |
| API 文档 | Swagger / ReDoc（drf-yasg） |
| WSGI / ASGI | Gunicorn / Uvicorn |

## 项目结构

```
backend/
├── application/            # Django 项目配置
│   ├── settings.py         # 主配置文件
│   ├── urls.py             # 根路由
│   ├── asgi.py             # ASGI 入口（WebSocket 支持）
│   ├── wsgi.py             # WSGI 入口
│   ├── celery.py           # Celery 应用配置
│   ├── dispatch.py         # 系统配置 / 字典缓存调度
│   ├── websocketConfig.py  # WebSocket 消费者
│   └── sse_views.py        # SSE 推送视图
├── conf/                   # 环境配置
│   ├── env.py              # 当前环境配置（.gitignore 排除）
│   └── env.example.py      # 配置模板
├── mainotebook/            # 业务代码主包
│   ├── system/             # 系统管理模块
│   │   ├── models.py       # 用户、角色、部门、菜单、权限等模型
│   │   ├── views/          # 系统管理视图
│   │   ├── services/       # 业务逻辑（注册、邮箱验证码等）
│   │   ├── fixtures/       # 初始化数据（JSON fixtures）
│   │   └── management/     # Django 管理命令
│   ├── content/            # 内容管理模块
│   │   ├── models.py       # 知识库、人设卡、评论、收藏等模型
│   │   ├── views/          # 内容视图
│   │   ├── services/       # 业务逻辑（审核、AI 审核、通知等）
│   │   ├── serializers/    # 序列化器
│   │   ├── tasks.py        # Celery 异步任务
│   │   └── tests/          # 测试代码
│   └── utils/              # 公共工具
│       ├── models.py       # CoreModel 基类
│       ├── filters.py      # 数据权限过滤器
│       ├── viewset.py      # CustomModelViewSet 基类
│       ├── serializers.py  # 通用序列化器基类
│       ├── middleware.py   # 中间件（API 日志、健康检查）
│       └── permission.py   # 权限控制
├── dvadmin/                # dvadmin3-celery 兼容层（勿删除）
├── docs/                   # 项目文档
│   ├── archive/            # 归档文档
│   └── README.md           # 文档索引
├── scripts/                # 运维脚本
│   ├── full_reset.py       # 全量删档清库脚本
│   └── setup_config.py     # 交互式配置生成脚本
├── manage.py               # Django CLI 入口
├── main.py                 # Uvicorn 启动入口
├── docker-compose.yml      # Docker 编排（PostgreSQL + Redis）
├── gunicorn_conf.py        # Gunicorn 生产配置
└── requirements.txt        # Python 依赖
```

## 快速开始

### 前置依赖

- Python 3.11+（推荐通过 Conda 管理）
- Docker（用于运行 PostgreSQL 和 Redis）
- Homebrew（macOS 包管理器）

### 1. 创建 Conda 环境

```bash
conda create -n mai_notebook python=3.11
conda activate mai_notebook
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 3. 启动基础服务

```bash
# 启动 PostgreSQL
docker-compose up -d

# 启动 Redis
docker start mai_notebook_redis
```

### 4. 配置环境变量

```bash
cp conf/env.example.py conf/env.py
# 根据实际环境修改数据库、Redis、邮件 SMTP、AI API Key 等配置
```

### 5. 数据库迁移与初始化

```bash
conda activate mai_notebook
python manage.py makemigrations
python manage.py migrate
python manage.py init -y
```

### 6. 启动服务

```bash
# 方式一：启动脚本（自动检查 Docker、数据库、Redis）
bash start.sh

# 方式二：直接启动
python main.py

# 方式三：Django 开发服务器
python manage.py runserver
```

### 7. 启动 Celery（异步任务）

```bash
# 在项目根目录执行（另开一个终端）

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

服务启动后：
- Swagger 文档：http://localhost:8000/
- ReDoc 文档：http://localhost:8000/redoc/

## 全量重置

```bash
# 基础重置（清库 + 重建 + 初始化基础数据）
python scripts/full_reset.py

# 包含测试用户
python scripts/full_reset.py --test
```

重置脚本会依次执行：删除并重建 PostgreSQL 数据库 → 清空 Redis → 删除上传文件和日志 → 清理迁移文件 → 重新生成 SECRET_KEY → 执行迁移 → 初始化基础数据。

## 核心功能模块

详细文档见 `docs/` 目录。

### 系统管理（mainotebook.system）

- 用户管理：邮箱验证注册、JWT 登录、用户 CRUD、头像管理
- 角色与权限：RBAC 权限模型（菜单权限 + 按钮权限 + 数据权限）
- 部门管理：树形部门结构
- 消息中心：站内消息 + WebSocket 实时推送
- 系统配置：键值对配置，支持分组
- 日志：操作日志 + 登录日志

### 内容管理（mainotebook.content）

- 知识库：CRUD、文件上传/下载、公开/私有、审核流程
- 人设卡：CRUD、文件上传/下载、bot_config.toml 版本解析、审核流程
- 评论系统：树形评论、回复、点赞/点踩、禁言管理
- 收藏系统：知识库/人设卡收藏
- 内容审核：人工审核 + AI 自动审核（Celery 异步）、批量审核
- 上传/下载记录：统计追踪

### 异步任务（Celery）

- AI 自动审核任务（auto_review_task）
- 批量审核任务（batch_auto_review_task）
- 定时任务调度（django-celery-beat）

## 角色与权限体系

| 角色 | key | 说明 | 数据权限 |
|------|-----|------|----------|
| 超级管理员 | superadmin | 系统最高权限 | 全部数据 |
| 管理员 | admin | 日常管理 | 全部数据 |
| 审核员 | reviewer | 内容审核 | 本部门及以下 |
| 普通用户 | user | 前台注册用户 | 仅本人数据 |

默认初始化用户：`superadmin` / `admin123456`、`admin` / `admin123456`

## API 路由概览

| 路径前缀 | 模块 | 说明 |
|----------|------|------|
| `/api/system/` | 系统管理 | 用户、角色、部门、菜单、字典、配置、日志 |
| `/api/content/knowledge/` | 知识库 | CRUD、文件管理、审核、收藏 |
| `/api/content/persona/` | 人设卡 | CRUD、文件管理、审核、收藏 |
| `/api/content/comments/` | 评论 | 发表、回复、点赞、删除 |
| `/api/content/review/` | 内容审核 | 待审核列表、批准、拒绝、统计 |
| `/api/content/moderation/` | AI 审核 | 内容检测、健康检查 |
| `/api/content/users/` | 用户扩展 | 上传历史、统计、收藏列表 |
| `/api/content/admin/users/` | 管理员扩展 | 禁言、封禁、角色管理 |
| `/api/register/` | 注册 | 邮箱注册、验证、重发 |
| `/api/token/` | 认证 | JWT 登录、刷新 |
| `ws/<service_uid>/` | WebSocket | 实时消息推送 |

## 测试

```bash
conda activate mai_notebook
pytest                              # 运行所有测试
pytest mainotebook/content/tests/   # 运行指定模块
```

## 生产部署

```bash
# Gunicorn（HTTP）
gunicorn application.wsgi:application -c gunicorn_conf.py

# Uvicorn（HTTP + WebSocket）
uvicorn application.asgi:application --host 0.0.0.0 --port 8000 --workers 4
```

## 注意事项

- `dvadmin/` 目录是 `dvadmin3-celery` 第三方包的兼容层，请勿删除
- `conf/env.py` 包含敏感配置，已被 `.gitignore` 排除，部署时需手动创建
- 所有模型使用 UUID 主键，前端传递 ID 时使用字符串格式
- 新用户注册通过邮箱验证流程，默认分配到「注册用户」部门和「普通用户」角色
- 前台内容 ViewSet 需设置 `extra_filter_class = []` 禁用后台数据级权限过滤
- Auth header 使用 `JWT` 前缀（不是 `Bearer`）
- 公开内容提交时自动触发 AI 审核（Celery 异步任务）

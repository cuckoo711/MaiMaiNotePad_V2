# Celery 定时任务使用指南

## 概述

MaiMaiNotePad 集成了 `dvadmin3-celery` 插件，提供了完整的定时任务管理功能。

## 功能特性

1. 前端可视化管理定时任务
2. 支持 Cron 表达式配置
3. 任务执行日志查看
4. 手动触发任务执行
5. 任务启用/禁用控制

## 安装状态

### 后端插件
- **包名**: `dvadmin3-celery`
- **版本**: 3.1.6
- **状态**: ✅ 已安装并配置

### 前端插件
- **包名**: `@great-dream/dvadmin3-celery-web`
- **版本**: 3.1.3
- **状态**: ✅ 已安装

## 菜单位置

登录系统后，在左侧导航栏可以看到：

```
定时任务
├── 任务管理    # 创建、编辑、删除定时任务
└── 任务日志    # 查看任务执行历史和结果
```

## 自动初始化

Celery 插件的菜单会在以下情况自动初始化：

1. **全量重置时**: 执行 `python backend/scripts/full_reset.py` 会自动初始化
2. **手动初始化**: 执行 `python -m mainotebook.system.fixtures.initialize` 会自动初始化

初始化过程会自动检测 `dvadmin3_celery` 是否已安装，如果已安装则导入菜单数据。

## 启动 Celery Worker

要使定时任务正常工作，需要启动 Celery Worker 和 Beat 调度器：

### 开发环境

```bash
# 激活 Conda 环境
conda activate mai_notebook

# 启动 Celery Worker（处理任务）
cd backend
celery -A application worker -l info

# 启动 Celery Beat（定时调度器）- 新开一个终端
cd backend
celery -A application beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### 生产环境

建议使用 Supervisor 或 systemd 管理 Celery 进程。

## 使用示例

### 创建定时任务

1. 进入"定时任务 > 任务管理"
2. 点击"新增"按钮
3. 填写任务信息：
   - 任务名称
   - 任务类型（选择已注册的 Celery 任务）
   - Cron 表达式（如：`0 2 * * *` 表示每天凌晨 2 点执行）
   - 任务参数（JSON 格式）
4. 保存并启用任务

### 查看任务日志

1. 进入"定时任务 > 任务日志"
2. 可以查看：
   - 任务执行时间
   - 执行状态（成功/失败）
   - 执行结果
   - 错误信息（如果失败）

## 已注册的定时任务

项目中已注册的 Celery 任务：

1. **AI 自动审核任务** (`mainotebook.content.tasks.auto_review_task`)
   - 功能：对知识库或人设卡进行 AI 内容审核
   - 参数：`content_id`（内容 ID）、`content_type`（knowledge/persona）

2. **批量 AI 审核任务** (`mainotebook.content.tasks.batch_auto_review_task`)
   - 功能：批量审核多个内容
   - 参数：`content_ids`（ID 列表）、`content_type`（knowledge/persona）

## 配置说明

### Redis 配置

Celery 使用 Redis 作为消息代理（Broker）：

- **Redis DB**: 3（独立于业务缓存的 DB 1）
- **配置位置**: `backend/conf/env.py` 中的 `CELERY_BROKER_DB`

### 结果存储

任务执行结果存储在 Django 数据库中：

- **表名**: `django_celery_results_taskresult`
- **配置**: `CELERY_RESULT_BACKEND = 'django-db'`

## 故障排查

### 菜单不显示

如果登录后看不到"定时任务"菜单：

1. 检查用户角色权限
2. 重新执行初始化：
   ```bash
   cd backend
   python -m mainotebook.system.fixtures.initialize
   ```
3. 清除浏览器缓存并重新登录

### 任务不执行

1. 确认 Celery Worker 和 Beat 都在运行
2. 检查 Redis 连接是否正常
3. 查看 Celery 日志输出
4. 确认任务已启用且 Cron 表达式正确

### 查看 Celery 日志

```bash
# 查看 Worker 日志
tail -f backend/logs/celery/worker.log

# 查看 Beat 日志
tail -f backend/logs/celery/beat.log
```

## 相关文档

- [Django Celery Beat 官方文档](https://django-celery-beat.readthedocs.io/)
- [Celery 官方文档](https://docs.celeryproject.org/)
- [Cron 表达式在线生成器](https://crontab.guru/)

## 注意事项

1. 定时任务的时区设置为 `Asia/Shanghai`
2. 修改任务配置后，Beat 调度器会自动重新加载
3. 长时间运行的任务建议设置超时时间
4. 生产环境建议配置任务失败重试策略

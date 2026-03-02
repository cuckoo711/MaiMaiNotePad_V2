# Celery 异步任务

## 概述

项目使用 Celery 处理异步任务，通过 `dvadmin3-celery` 插件集成。Broker 使用 Redis（DB 3），结果存储使用 Django 数据库（django-celery-results），定时任务调度使用 django-celery-beat。

## 配置

### Celery 应用

定义在 `application/celery.py`，应用名为 `application`。

```python
# application/celery.py
app = Celery("application")
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
```

### 关键配置项

| 配置 | 值 | 说明 |
|------|-----|------|
| CELERY_BROKER_URL | `redis://:<password>@127.0.0.1:6379/3` | Broker 地址 |
| CELERY_RESULT_BACKEND | `django-db` | 结果存储 |
| CELERY_BEAT_SCHEDULER | `django_celery_beat.schedulers.DatabaseScheduler` | Beat 调度器 |
| CELERY_TIMEZONE | `Asia/Shanghai` | 时区 |
| CELERY_TASK_SERIALIZER | `json` | 任务序列化格式 |

## 启动

### 一键启动脚本

在项目根目录执行（另开一个终端）：

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

脚本自动适配 macOS / Linux：
- macOS：使用 `solo` 池（避免 fork 安全问题）
- Linux：使用 `prefork` 池（4 并发）

日志输出到 `backend/logs/celery/` 目录。

### 手动启动

```bash
# Worker
celery -A application.celery:app worker --loglevel=info --pool=solo

# Beat
celery -A application.celery:app beat --loglevel=info --scheduler=django_celery_beat.schedulers:DatabaseScheduler
```

## 已注册任务

### AI 自动审核

```python
# mainotebook/content/tasks.py

# 单条审核（最多重试 3 次，间隔 60 秒）
auto_review_task.delay(str(content_id), 'persona')

# 批量审核
batch_auto_review_task.delay(content_ids, 'knowledge')
```

### 定时任务

通过 Django Admin 的 django-celery-beat 界面管理定时任务。

## 监控

任务执行结果存储在 `django_celery_results_taskresult` 表中，可通过 Django Admin 查看。

## 相关文件

- Celery 配置：`application/celery.py`
- 启动脚本：根目录 `start_celery.sh`
- 内容审核任务：`mainotebook/content/tasks.py`
- dvadmin3-celery 兼容层：`dvadmin/`

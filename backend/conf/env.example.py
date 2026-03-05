import os

from application.settings import BASE_DIR

# ================================================= #
# *************** mysql数据库 配置  *************** #
# ================================================= #
# 数据库 ENGINE ，默认演示使用 sqlite3 数据库，正式环境建议使用 mysql 数据库
# sqlite3 设置
# DATABASE_ENGINE = "django.db.backends.sqlite3"
# DATABASE_NAME = os.path.join(BASE_DIR, "db.sqlite3")

# 使用mysql时，改为此配置
DATABASE_ENGINE = "django.db.backends.mysql"
DATABASE_NAME = 'django-vue3-admin' # mysql 时使用

# 数据库地址 改为自己数据库地址
DATABASE_HOST = '127.0.0.1'
# # 数据库端口
DATABASE_PORT = 3306
# # 数据库用户名
DATABASE_USER = "root"
# # 数据库密码
DATABASE_PASSWORD = 'MAINOTEBOOK3'

# 表前缀
TABLE_PREFIX = "mainotebook_"
# ================================================= #
# ******** redis配置，无redis 可不进行配置  ******** #
# ================================================= #
# Redis 用于：
# - 用户会话缓存
# - Celery 消息队列（异步任务）
# - 人设卡上传限额管理（每日 10 次限制）
# - 验证码重试次数和冷却期管理
REDIS_DB = 1
CELERY_BROKER_DB = 3
REDIS_PASSWORD = 'MAINOTEBOOK3'
REDIS_HOST = '127.0.0.1'
REDIS_URL = f'redis://:{REDIS_PASSWORD or ""}@{REDIS_HOST}:6379'
# ================================================= #
# ****************** 功能 启停  ******************* #
# ================================================= #
DEBUG = True
# 启动登录详细概略获取(通过调用api获取ip详细地址。如果是内网，关闭即可)
ENABLE_LOGIN_ANALYSIS_LOG = True
# 登录接口 /api/token/ 是否需要验证码认证，用于测试，正式环境建议取消
LOGIN_NO_CAPTCHA_AUTH = True
# ================================================= #
# ****************** 其他 配置  ******************* #
# ================================================= #

ALLOWED_HOSTS = ["*"]
# 列权限中排除App应用
COLUMN_EXCLUDE_APPS = []

# ================================================= #
# ************** 人设卡上传功能配置 *************** #
# ================================================= #
# 人设卡上传限额配置
# 每个用户每天最多上传的人设卡数量（默认 10 个）
PERSONA_UPLOAD_DAILY_LIMIT = 10

# 验证码配置
# 验证码最大重试次数（默认 10 次）
CAPTCHA_MAX_RETRY_COUNT = 10
# 验证码冷却期（秒，默认 60 秒）
CAPTCHA_COOLDOWN_SECONDS = 60

# 文件上传配置
# 允许的最小文件大小（字节，默认 1KB）
MIN_FILE_SIZE = 1024
# 允许的最大文件大小（字节，默认 2MB）
MAX_FILE_SIZE = 2 * 1024 * 1024

# 注意：
# 1. Redis 必须正常运行，用于上传限额和验证码管理
# 2. Celery Worker 必须启动，用于异步审核任务
# 3. 文件存储路径：MEDIA_ROOT/persona_cards/

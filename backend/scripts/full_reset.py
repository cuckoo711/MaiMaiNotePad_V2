#!/usr/bin/env python
"""
MaiMaiNotePad 全量重置脚本

功能：
1. 删除并重建 PostgreSQL 数据库
2. 清空 Redis 缓存（业务缓存 + Celery Broker）
3. 删除所有上传文件（media 目录）
4. 删除日志文件
5. 清理迁移文件
6. 重新生成 Django SECRET_KEY
7. 重新执行数据库迁移

警告：此操作不可逆，所有数据将被永久删除！
"""

import os
import sys
import shutil
import secrets
import string
import re

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import redis

# ================================================= #
# ****************** 配置区域 ****************** #
# ================================================= #

# 数据库配置（直接硬编码，避免 Django 循环导入）
DATABASE_NAME = "mai_notebook"
DATABASE_USER = "mai_notebook"
DATABASE_PASSWORD = "5IaGmT4LVCjVG7XTKlwWDtBOZ7MD6b_qQBJyqBdfGs8"
DATABASE_HOST = "127.0.0.1"
DATABASE_PORT = 5432

# Redis 配置
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_PASSWORD = "F8M7j6coq__Ck_eQqUfJOnrUztAhv7-6"
REDIS_DB = 1           # 业务缓存
CELERY_BROKER_DB = 3   # Celery Broker

# 路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA_DIR = os.path.join(BASE_DIR, "media")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
SETTINGS_FILE = os.path.join(BASE_DIR, "application", "settings.py")

# 将 BASE_DIR 添加到 Python 路径，确保可以导入 application 模块
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# 迁移文件排除目录
MIGRATION_EXCLUDE_DIRS = {"venv", ".venv", "node_modules", "__pycache__"}


def confirm_reset() -> bool:
    """二次确认，防止误操作

    Returns:
        bool: 用户确认返回 True，否则返回 False
    """
    print("=" * 60)
    print("⚠️  警告：即将执行全量删档清库操作！")
    print("=" * 60)
    print("以下数据将被永久删除：")
    print("  - PostgreSQL 数据库（mai_notebook）")
    print("  - Redis 缓存（DB 1 业务缓存 + DB 3 Celery）")
    print("  - 所有上传文件（media 目录）")
    print("  - 所有日志文件（logs 目录）")
    print("  - 所有迁移文件")
    print("  - Django SECRET_KEY 将被重新生成")
    print("=" * 60)

    answer = input("\n请输入 'YES' 确认执行: ").strip()
    return answer.lower() == "yes"


def reset_database() -> bool:
    """删除并重建 PostgreSQL 数据库

    Returns:
        bool: 操作成功返回 True，否则返回 False
    """
    print("\n[1/8] 重置 PostgreSQL 数据库...")

    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            host=DATABASE_HOST,
            port=DATABASE_PORT,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # 断开所有现有连接
        print("  → 断开所有活跃连接...")
        cursor.execute(
            """
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = %s
            AND pid <> pg_backend_pid();
            """,
            (DATABASE_NAME,),
        )

        # 删除数据库
        print(f"  → 删除数据库 {DATABASE_NAME}...")
        cursor.execute(f'DROP DATABASE IF EXISTS "{DATABASE_NAME}";')

        # 重建数据库
        print(f"  → 创建数据库 {DATABASE_NAME}...")
        cursor.execute(
            f'CREATE DATABASE "{DATABASE_NAME}" OWNER "{DATABASE_USER}";'
        )

        cursor.close()
        conn.close()
        print("  ✅ 数据库重置完成")
        return True

    except Exception as e:
        print(f"  ❌ 数据库重置失败: {e}")
        return False


def flush_redis() -> bool:
    """清空 Redis 缓存（业务缓存 + Celery Broker）

    Returns:
        bool: 操作成功返回 True，否则返回 False
    """
    print("\n[2/8] 清空 Redis 缓存...")

    try:
        for db, label in [(REDIS_DB, "业务缓存"), (CELERY_BROKER_DB, "Celery Broker")]:
            r = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                db=db,
            )
            key_count = r.dbsize()
            r.flushdb()
            print(f"  → DB {db}（{label}）：已清除 {key_count} 个键")
            r.close()

        print("  ✅ Redis 缓存清空完成")
        return True

    except Exception as e:
        print(f"  ❌ Redis 清空失败: {e}")
        return False


def clean_media() -> bool:
    """删除所有上传文件（清空 media 目录并重建空目录结构）

    Returns:
        bool: 操作成功返回 True，否则返回 False
    """
    print("\n[3/8] 清理上传文件...")

    try:
        if os.path.exists(MEDIA_DIR):
            # 统计文件数量
            file_count = sum(
                len(files) for _, _, files in os.walk(MEDIA_DIR)
            )
            shutil.rmtree(MEDIA_DIR)
            print(f"  → 已删除 {file_count} 个文件")
        else:
            print("  → media 目录不存在，跳过")

        # 重建空目录结构（仅保留业务必需的子目录）
        for subdir in ["avatar", "files"]:
            os.makedirs(os.path.join(MEDIA_DIR, subdir), exist_ok=True)

        print("  ✅ 上传文件清理完成，已重建空目录结构")
        return True

    except Exception as e:
        print(f"  ❌ 文件清理失败: {e}")
        return False


def clean_logs() -> bool:
    """清理日志文件

    Returns:
        bool: 操作成功返回 True，否则返回 False
    """
    print("\n[4/8] 清理日志文件...")

    try:
        if os.path.exists(LOGS_DIR):
            file_count = sum(
                len(files) for _, _, files in os.walk(LOGS_DIR)
            )
            shutil.rmtree(LOGS_DIR)
            print(f"  → 已删除 {file_count} 个日志文件")
        else:
            print("  → logs 目录不存在，跳过")

        os.makedirs(LOGS_DIR, exist_ok=True)
        print("  ✅ 日志清理完成")
        return True

    except Exception as e:
        print(f"  ❌ 日志清理失败: {e}")
        return False


def clean_migrations() -> bool:
    """删除所有迁移文件（保留 __init__.py）

    Returns:
        bool: 操作成功返回 True，否则返回 False
    """
    print("\n[5/8] 清理迁移文件...")

    try:
        deleted_count = 0
        for root, dirs, files in os.walk(BASE_DIR):
            # 排除不需要扫描的目录
            dirs[:] = [d for d in dirs if d not in MIGRATION_EXCLUDE_DIRS]

            if "migrations" in dirs:
                migration_dir = os.path.join(root, "migrations")
                for mig_root, _, mig_files in os.walk(migration_dir):
                    for f in mig_files:
                        if f != "__init__.py":
                            filepath = os.path.join(mig_root, f)
                            os.remove(filepath)
                            deleted_count += 1

        print(f"  → 已删除 {deleted_count} 个迁移文件")
        print("  ✅ 迁移文件清理完成")
        return True

    except Exception as e:
        print(f"  ❌ 迁移文件清理失败: {e}")
        return False


def generate_secret_key(length: int = 50) -> str:
    """生成新的 Django SECRET_KEY

    Args:
        length: 密钥长度，默认 50

    Returns:
        str: 新生成的密钥字符串
    """
    chars = string.ascii_letters + string.digits + string.punctuation
    # 排除可能导致字符串解析问题的字符
    chars = chars.replace("'", "").replace('"', "").replace("\\", "")
    return "".join(secrets.choice(chars) for _ in range(length))


def refresh_secret_key() -> bool:
    """在 settings.py 中替换 SECRET_KEY

    Returns:
        bool: 操作成功返回 True，否则返回 False
    """
    print("\n[6/8] 重新生成 Django SECRET_KEY...")

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        new_key = generate_secret_key()

        # 匹配 SECRET_KEY = "..." 或 SECRET_KEY = '...'
        pattern = r'(SECRET_KEY\s*=\s*)["\'].*?["\']'
        replacement = f'\\1"{new_key}"'

        new_content, count = re.subn(pattern, replacement, content, count=1)

        if count == 0:
            print("  ❌ 未找到 SECRET_KEY 配置项")
            return False

        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"  → 新密钥: {new_key[:10]}...（已截断显示）")
        print("  ✅ SECRET_KEY 已更新")
        return True

    except Exception as e:
        print(f"  ❌ SECRET_KEY 更新失败: {e}")
        return False


def run_migrations() -> bool:
    """执行 Django 数据库迁移（makemigrations + migrate）

    Returns:
        bool: 操作成功返回 True，否则返回 False
    """
    print("\n[7/8] 执行数据库迁移...")

    try:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "application.settings")

        ret = os.system(f'cd "{BASE_DIR}" && "{sys.executable}" manage.py makemigrations')
        if ret != 0:
            print("  ❌ makemigrations 失败")
            return False

        ret = os.system(f'cd "{BASE_DIR}" && "{sys.executable}" manage.py migrate')
        if ret != 0:
            print("  ❌ migrate 失败")
            return False

        print("  ✅ 数据库迁移完成")
        return True

    except Exception as e:
        print(f"  ❌ 数据库迁移失败: {e}")
        return False


def init_data(include_test: bool = False) -> bool:
    """执行初始化数据（部门、角色、用户、菜单、权限、字典、系统配置等）

    通过 mainotebook.system.fixtures.initialize.Initialize 加载 JSON fixtures。

    Args:
        include_test: 是否同时创建测试用户

    Returns:
        bool: 操作成功返回 True，否则返回 False
    """
    print("\n[8/8] 初始化基础数据...")

    try:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "application.settings")

        # 确保 Django 已初始化
        import django
        django.setup()

        from mainotebook.system.fixtures.initialize import Initialize

        initializer = Initialize(reset=True, app="mainotebook.system")
        if include_test:
            print("  → 包含测试用户初始化...")
            initializer.run_with_test_data()
        else:
            initializer.run()

        print("  ✅ 基础数据初始化完成")
        return True

    except Exception as e:
        print(f"  ❌ 数据初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main() -> None:
    """主函数，按顺序执行全量重置

    支持 --test 参数，同时创建测试用户。
    """
    if not confirm_reset():
        print("\n已取消操作。")
        sys.exit(0)

    include_test = "--test" in sys.argv

    print("\n🚀 开始执行全量重置...\n")

    steps = [
        ("数据库重置", reset_database),
        ("Redis 清空", flush_redis),
        ("上传文件清理", clean_media),
        ("日志清理", clean_logs),
        ("迁移文件清理", clean_migrations),
        ("SECRET_KEY 刷新", refresh_secret_key),
        ("数据库迁移", run_migrations),
        ("基础数据初始化", lambda: init_data(include_test=include_test)),
    ]

    results = []
    for name, func in steps:
        success = func()
        results.append((name, success))
        if not success and name in ("数据库重置", "数据库迁移", "基础数据初始化"):
            # 关键步骤失败则中止
            print(f"\n❌ 关键步骤「{name}」失败，中止后续操作。")
            break

    # 输出汇总
    print("\n" + "=" * 60)
    print("📋 执行结果汇总")
    print("=" * 60)
    for name, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {status}  {name}")
    print("=" * 60)

    all_success = all(s for _, s in results)
    if all_success:
        print("\n🎉 全量重置完成！可以启动服务了。")
    else:
        print("\n⚠️  部分步骤失败，请检查上方日志。")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""交互式配置生成脚本

收集用户输入的邮件 SMTP、AI 审核等配置，结合自动生成的数据库/Redis 密码，
生成 conf/env.py 配置文件。

用法:
    python setup_config.py                          # 交互式生成配置
    python setup_config.py --pg-pass XX --redis-pass YY  # 指定密码生成配置
    python setup_config.py --gen-password            # 仅生成并输出随机密码
"""

import argparse
import os
import secrets
import string
import sys
from pathlib import Path
from typing import Optional

# ==================== 常量 ====================

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / "conf" / "env.py"

# 数据库默认值
PG_DB = "mai_notebook"
PG_USER = "mai_notebook"
PG_HOST = "127.0.0.1"
PG_PORT = 5432

REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379


# ==================== 工具函数 ====================

class Colors:
    """终端颜色码"""
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"


def _color_supported() -> bool:
    """检测终端是否支持颜色"""
    if os.name == "nt":
        try:
            os.system("")
            return True
        except Exception:
            return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


if not _color_supported():
    for attr in ["RED", "GREEN", "YELLOW", "CYAN", "NC"]:
        setattr(Colors, attr, "")


def info(msg: str) -> None:
    """输出信息"""
    print(f"  {Colors.CYAN}ℹ{Colors.NC} {msg}")


def success(msg: str) -> None:
    """输出成功"""
    print(f"  {Colors.GREEN}✓{Colors.NC} {msg}")


def warn(msg: str) -> None:
    """输出警告"""
    print(f"  {Colors.YELLOW}⚠{Colors.NC} {msg}")


def generate_password(length: int = 32) -> str:
    """生成安全随机密码

    Args:
        length: 密码长度

    Returns:
        str: 随机密码（仅字母和数字，避免 shell 转义问题）
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ==================== 配置读取 ====================

def read_existing_config() -> dict:
    """读取现有配置文件中的配置"""
    config = {}
    if not ENV_FILE.exists():
        return config

    try:
        # 简单解析 env.py 文件
        # 注意：这里不使用 import，而是直接解析文本，避免执行代码
        content = ENV_FILE.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                
                if key == "EMAIL_HOST":
                    config["email_host"] = value
                elif key == "EMAIL_PORT":
                    config["email_port"] = value
                elif key == "EMAIL_USE_TLS":
                    config["email_use_tls"] = value
                elif key == "EMAIL_HOST_USER":
                    config["email_user"] = value
                elif key == "EMAIL_HOST_PASSWORD":
                    config["email_password"] = value
                elif key == "DEFAULT_FROM_EMAIL":
                    config["email_from"] = value
                elif key == "SILICONFLOW_API_KEY":
                    # 处理 os.getenv 形式
                    if "os.getenv" in value:
                        # 提取默认值: os.getenv("KEY", "VALUE")
                        parts = value.split(",")
                        if len(parts) > 1:
                            config["ai_api_key"] = parts[1].strip().strip(")").strip('"').strip("'")
                    else:
                        config["ai_api_key"] = value
                elif key == "FRONTEND_URL":
                    config["frontend_url"] = value
                elif key == "DEBUG":
                    config["debug"] = value
                elif key == "DATABASE_PASSWORD":
                    config["pg_password"] = value
                elif key == "REDIS_PASSWORD":
                    config["redis_password"] = value
    except Exception as e:
        warn(f"读取现有配置失败: {e}")
    
    return config

# ==================== 交互式输入 ====================

def prompt_input(label: str, default: str = "") -> str:
    """交互式输入，支持默认值

    Args:
        label: 提示标签
        default: 默认值

    Returns:
        str: 用户输入值或默认值
    """
    if default:
        prompt_text = f"  {label} [{default}]: "
    else:
        prompt_text = f"  {label}: "
    value = input(prompt_text).strip()
    return value if value else default


def confirm(msg: str) -> bool:
    """确认操作

    Args:
        msg: 确认提示

    Returns:
        bool: 用户是否确认
    """
    while True:
        reply = input(f"  {msg} (y/n): ").strip().lower()
        if reply in ("y", "yes"):
            return True
        if reply in ("n", "no"):
            return False


def interactive_config(existing_config: dict = None) -> dict:
    """交互式收集配置信息

    用户可以无限次重新输入，直到确认为止。

    Args:
        existing_config: 现有配置字典，用于默认值

    Returns:
        dict: 配置字典
    """
    if existing_config is None:
        existing_config = {}

    while True:
        print(f"\n{Colors.CYAN}--- 邮件 SMTP 配置 ---{Colors.NC}")
        print("  （用于发送注册验证码邮件，可留空稍后在 conf/env.py 中配置）")
        
        default_host = existing_config.get("email_host", "smtp.qq.com")
        email_host = prompt_input("SMTP 服务器地址", default_host)
        
        default_port = existing_config.get("email_port", "587")
        email_port = prompt_input("SMTP 端口", default_port)
        
        default_tls = existing_config.get("email_use_tls", "true")
        email_use_tls = prompt_input("启用 TLS (true/false)", str(default_tls).lower())
        
        default_user = existing_config.get("email_user", "")
        email_user = prompt_input("发件人邮箱", default_user)
        
        default_pass = existing_config.get("email_password", "")
        # 密码特殊处理：如果不输入且有默认值，则保留默认值
        pass_prompt = f"邮箱密码/授权码 [{'******' if default_pass else ''}]"
        email_password = input(f"  {pass_prompt}: ").strip()
        if not email_password and default_pass:
            email_password = default_pass
            
        default_from = existing_config.get("email_from", email_user)
        email_from = prompt_input("发件人显示地址", default_from)

        print(f"\n{Colors.CYAN}--- AI 内容审核配置 ---{Colors.NC}")
        print("  （硅基流动 API Key，用于 AI 自动审核，可留空跳过）")
        print("  （获取地址: https://cloud.siliconflow.cn/）")
        
        default_ai_key = existing_config.get("ai_api_key", "")
        ai_api_key = prompt_input("硅基流动 API Key", default_ai_key)

        print(f"\n{Colors.CYAN}--- 其他配置 ---{Colors.NC}")
        
        default_frontend = existing_config.get("frontend_url", "http://localhost:5173")
        frontend_url = prompt_input("前端地址", default_frontend)
        
        default_debug = existing_config.get("debug", "true")
        debug_mode = prompt_input("调试模式 (true/false)", str(default_debug).lower())

        # 展示配置摘要
        print(f"\n{Colors.YELLOW}--- 配置确认 ---{Colors.NC}")
        print(f"  邮件服务器:   {email_host}:{email_port} (TLS: {email_use_tls})")
        print(f"  发件人:       {email_user or '(未配置)'}")
        print(f"  邮箱密码:     {'*' * len(email_password) if email_password else '(未配置)'}")
        print(f"  发件人地址:   {email_from or '(未配置)'}")
        mask = '*' * 8 + ai_api_key[-8:] if len(ai_api_key) > 8 else (ai_api_key or '(未配置)')
        print(f"  AI API Key:   {mask}")
        print(f"  前端地址:     {frontend_url}")
        print(f"  调试模式:     {debug_mode}")

        if confirm("\n确认以上配置？输入 n 可重新输入"):
            return {
                "email_host": email_host,
                "email_port": email_port,
                "email_use_tls": str(email_use_tls).lower() == "true",
                "email_user": email_user,
                "email_password": email_password,
                "email_from": email_from,
                "ai_api_key": ai_api_key,
                "frontend_url": frontend_url,
                "debug": str(debug_mode).lower() == "true",
            }
        print("\n  好的，请重新输入配置。\n")


# ==================== 配置文件生成 ====================

def write_env_file(pg_password: str, redis_password: str, config: dict) -> None:
    """生成 conf/env.py 配置文件

    Args:
        pg_password: PostgreSQL 密码
        redis_password: Redis 密码
        config: 交互式收集的配置字典
    """
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)

    # 使用列表拼接避免 f-string 嵌套问题
    # REDIS_URL 行在生成的 env.py 中需要是一个 f-string，引用自身的变量
    redis_url_line = 'REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:' + str(REDIS_PORT) + '"'

    lines = [
        'import os',
        '',
        'from application.settings import BASE_DIR',
        '',
        '# ================================================= #',
        '# *************** 数据库配置  *************** #',
        '# ================================================= #',
        'DATABASE_ENGINE = "django.db.backends.postgresql"',
        f'DATABASE_NAME = "{PG_DB}"',
        f'DATABASE_HOST = "{PG_HOST}"',
        f'DATABASE_PORT = {PG_PORT}',
        f'DATABASE_USER = "{PG_USER}"',
        f'DATABASE_PASSWORD = "{pg_password}"',
        '',
        '# 表前缀',
        'TABLE_PREFIX = "mainotebook_"',
        '',
        '# ================================================= #',
        '# ******** Redis 配置  ******** #',
        '# ================================================= #',
        'REDIS_DB = 1',
        'CELERY_BROKER_DB = 3',
        f'REDIS_PASSWORD = "{redis_password}"',
        f'REDIS_HOST = "{REDIS_HOST}"',
        redis_url_line,
        '',
        '# ================================================= #',
        '# ****************** 功能 启停  ******************* #',
        '# ================================================= #',
        f'DEBUG = {config["debug"]}',
        'ENABLE_LOGIN_ANALYSIS_LOG = False',
        'LOGIN_NO_CAPTCHA_AUTH = False',
        '',
        '# ================================================= #',
        '# ************** AI 内容审核配置 *************** #',
        '# ================================================= #',
        f'SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "{config["ai_api_key"]}")',
        '',
        '# ================================================= #',
        '# ************** 邮件 SMTP 配置 *************** #',
        '# ================================================= #',
        f'EMAIL_HOST = "{config["email_host"]}"',
        f'EMAIL_PORT = {config["email_port"]}',
        f'EMAIL_USE_TLS = {config["email_use_tls"]}',
        f'EMAIL_HOST_USER = "{config["email_user"]}"',
        f'EMAIL_HOST_PASSWORD = "{config["email_password"]}"',
        f'DEFAULT_FROM_EMAIL = "{config["email_from"]}"',
        '',
        '# ================================================= #',
        '# ****************** 其他 配置  ******************* #',
        '# ================================================= #',
        f'FRONTEND_URL = "{config["frontend_url"]}"',
        'ALLOWED_HOSTS = ["*"]',
        'COLUMN_EXCLUDE_APPS = []',
        '',
    ]

    content = "\n".join(lines)
    ENV_FILE.write_text(content, encoding="utf-8")
    success(f"配置文件已写入: {ENV_FILE}")


# ==================== 主入口 ====================

def main() -> None:
    """主函数

    支持三种模式：
    1. --gen-password: 仅输出随机密码（供 shell 脚本调用）
    2. 指定 --pg-pass / --redis-pass: 使用指定密码 + 交互式配置
    3. 无参数: 自动生成密码 + 交互式配置
    """
    parser = argparse.ArgumentParser(description="麦麦笔记本 - 交互式配置生成")
    parser.add_argument("--pg-pass", help="PostgreSQL 密码（由启动脚本传入）")
    parser.add_argument("--redis-pass", help="Redis 密码（由启动脚本传入）")
    parser.add_argument("--gen-password", action="store_true",
                        help="仅生成并输出两行密码（pg\\nredis），供 shell 脚本读取")
    args = parser.parse_args()

    # 仅生成密码模式
    if args.gen_password:
        print(generate_password())
        print(generate_password())
        return

    # 确定密码
    # 如果传入了密码，使用传入的；否则先尝试从现有配置读取；最后再生成随机的
    existing_config = read_existing_config()
    
    pg_password = args.pg_pass or existing_config.get("pg_password") or generate_password()
    redis_password = args.redis_pass or existing_config.get("redis_password") or generate_password()

    print(f"\n{Colors.CYAN}{'=' * 50}")
    print("  麦麦笔记本 · 配置生成向导")
    print(f"{'=' * 50}{Colors.NC}")
    
    if existing_config:
        info("检测到现有配置文件，已加载默认值")

    info(f"PostgreSQL 密码: {pg_password[:8]}...（已自动生成或保留）")
    info(f"Redis 密码:      {redis_password[:8]}...（已自动生成或保留）")

    # 交互式收集其他配置
    config = interactive_config(existing_config)

    # 写入配置文件
    write_env_file(pg_password, redis_password, config)

    print()
    success("配置完成，可以继续启动后端服务了。")


if __name__ == "__main__":
    main()

import multiprocessing
import os
import sys
import signal
import argparse

root_path = os.getcwd()
sys.path.append(root_path)
import uvicorn
from application.settings import LOGGING

def handle_sigint(signum, frame):
    """处理 SIGINT 信号，快速退出"""
    print("\n正在停止服务...")
    sys.exit(0)

if __name__ == '__main__':
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='麦麦笔记本后端服务')
    parser.add_argument('--reload', action='store_true', help='启用自动重载（调试模式）')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址（默认: 0.0.0.0）')
    parser.add_argument('--port', type=int, default=8000, help='监听端口（默认: 8000）')
    args = parser.parse_args()
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, handle_sigint)
    
    multiprocessing.freeze_support()
    
    # 自动重载模式下不使用多进程
    workers = 1 if args.reload else 4
    if os.sys.platform.startswith('win'):
        # Windows操作系统
        workers = None
    
    # 配置 uvicorn
    uvicorn.run(
        "application.asgi:application",
        reload=args.reload,
        host=args.host,
        port=args.port,
        workers=workers,
        log_config=LOGGING,
        timeout_graceful_shutdown=5  # 优雅关闭超时时间设为 5 秒
    )

import multiprocessing
import os
import sys
import warnings

# 忽略 drf-yasg 导致的 pkg_resources 废弃警告
warnings.filterwarnings("ignore", category=UserWarning, message="pkg_resources is deprecated as an API")

root_path = os.getcwd()
sys.path.append(root_path)
import uvicorn
from application.settings import LOGGING

if __name__ == '__main__':
    multiprocessing.freeze_support()
    workers = 4
    if os.sys.platform.startswith('win'):
        # Windows操作系统
        workers = None
    uvicorn.run("application.asgi:application", reload=False, host="0.0.0.0", port=8000, workers=workers,
                log_config=LOGGING)

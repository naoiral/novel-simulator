"""日志配置 — 统一管理项目日志输出。"""

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging(log_dir=None):
    """配置项目日志。

    - 控制台输出 INFO 及以上
    - 文件输出 DEBUG 及以上（自动轮转，最大 5MB，保留 3 个备份）
    """
    if log_dir is None:
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "logs")
    os.makedirs(log_dir, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # 避免重复添加 handler
    if root.handlers:
        return

    # 格式
    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    root.addHandler(console)

    # 文件
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

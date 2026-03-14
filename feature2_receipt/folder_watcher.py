"""watchdog 文件夹监控模块"""

import time
from pathlib import Path
from typing import Callable

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from shared.logger import get_logger

logger = get_logger("folder_watcher")

# 支持的图片格式
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".heif", ".heic"}


class ReceiptImageHandler(FileSystemEventHandler):
    """监听文件夹中新增的图片文件"""

    def __init__(self, callback: Callable[[Path], None]):
        self.callback = callback

    def on_created(self, event: FileCreatedEvent):
        if event.is_directory:
            return
        filepath = Path(event.src_path)
        if filepath.suffix.lower() in SUPPORTED_EXTENSIONS:
            logger.info("检测到新图片: %s", filepath.name)
            # 等待文件写入完成
            self._wait_for_stable(filepath)
            self.callback(filepath)

    @staticmethod
    def _wait_for_stable(filepath: Path, timeout: float = 10.0, interval: float = 0.5):
        """等待文件写入稳定 (大小不再变化)"""
        prev_size = -1
        elapsed = 0.0
        while elapsed < timeout:
            try:
                current_size = filepath.stat().st_size
                if current_size == prev_size and current_size > 0:
                    return
                prev_size = current_size
            except OSError:
                pass
            time.sleep(interval)
            elapsed += interval
        logger.warning("文件写入超时: %s", filepath.name)


def start_watching(
    watch_folder: str,
    callback: Callable[[Path], None],
    recursive: bool = False,
) -> Observer:
    """启动文件夹监控

    Args:
        watch_folder: 监控目录路径
        callback: 发现新图片时的回调函数 (接收 Path 参数)
        recursive: 是否递归监控子目录

    Returns:
        Observer 实例 (可调用 .stop() 停止)
    """
    watch_path = Path(watch_folder)
    watch_path.mkdir(parents=True, exist_ok=True)

    handler = ReceiptImageHandler(callback)
    observer = Observer()
    observer.schedule(handler, str(watch_path), recursive=recursive)
    observer.start()

    logger.info("开始监控文件夹: %s", watch_path)
    return observer

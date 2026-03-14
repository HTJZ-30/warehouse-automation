"""结构化 JSON 日志模块"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """输出结构化 JSON 日志行"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        # 附加自定义字段
        for key in ("sku", "supplier", "receipt_no", "action", "confidence"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        return json.dumps(log_entry, ensure_ascii=False)


def get_logger(name: str, log_dir: str = "logs", level: str = "INFO") -> logging.Logger:
    """创建或获取一个结构化 JSON 日志器

    Args:
        name: 日志器名称 (通常为模块名)
        log_dir: 日志文件输出目录
        level: 日志级别
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 控制台输出 (人类可读)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(console)

    # 文件输出 (JSON)
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(
        log_path / f"{name}.jsonl", encoding="utf-8"
    )
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)

    return logger

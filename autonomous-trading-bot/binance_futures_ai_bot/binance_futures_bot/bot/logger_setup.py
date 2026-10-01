"""Cấu hình logging: in ra console đồng thời ghi vào file xoay vòng (rotating)."""
import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger(name: str = "futures_bot", cfg: dict = None) -> logging.Logger:
    log_cfg = (cfg or {}).get("logging", {})
    level_name = log_cfg.get("level", "INFO")
    log_file = log_cfg.get("file", "logs/bot.log")

    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:  # tránh gắn handler trùng nếu setup_logger được gọi nhiều lần
        return logger

    logger.setLevel(getattr(logging, level_name.upper(), logging.INFO))

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    file_handler = RotatingFileHandler(
        log_file, maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger

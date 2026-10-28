"""
Logging Subsystem for IT Support Automation Suite
Provides formatted file logging and in-memory log capturing for UI presentation.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from collections import deque
from typing import List, Callable, Optional

# In-memory buffer of recent logs for GUI presentation
_memory_logs = deque(maxlen=1000)
_log_listeners: List[Callable[[str], None]] = []


class InMemoryHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            _memory_logs.append(msg)
            for listener in _log_listeners:
                try:
                    listener(msg)
                except Exception:
                    pass
        except Exception:
            self.handleError(record)


def setup_logging(log_file_path: str = "logs/it_support.log", level: int = logging.INFO) -> logging.Logger:
    """Configures root logger with file handler, console handler, and in-memory handler."""
    logger = logging.getLogger("ITSupportSuite")
    logger.setLevel(level)

    # Avoid duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Ensure log directory exists
    log_dir = os.path.dirname(os.path.abspath(log_file_path))
    os.makedirs(log_dir, exist_ok=True)

    # File handler with rotation (up to 5MB, 3 backups)
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Stream (console) handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # In-memory handler for UI
    mem_handler = InMemoryHandler()
    mem_handler.setFormatter(formatter)
    logger.addHandler(mem_handler)

    return logger


def add_log_listener(callback: Callable[[str], None]):
    """Registers a callback to receive real-time log messages (e.g. for GUI)."""
    if callback not in _log_listeners:
        _log_listeners.append(callback)


def remove_log_listener(callback: Callable[[str], None]):
    if callback in _log_listeners:
        _log_listeners.remove(callback)


def get_memory_logs() -> List[str]:
    """Returns a snapshot of the recent log buffer."""
    return list(_memory_logs)


from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("/var/log/SysTrayWeather")
LOG_FILE = LOG_DIR / "systrayweather.log"
_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("systrayweather")
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(_FORMAT)

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except PermissionError:
        local_dir = Path.home() / ".local" / "log" / "systrayweather"
        local_dir.mkdir(parents=True, exist_ok=True)
        local_file = local_dir / "systrayweather.log"
        file_handler = RotatingFileHandler(
            local_file, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.warning("Falling back to %s (no permission for /var/log/SysTrayWeather)", local_file)

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger

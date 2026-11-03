"""Structured logging setup for InspectLog."""

import logging
import os
import sys
from datetime import datetime

from inspectlog.constants import APP_NAME, APP_TEMP_DIR


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure structured logging with file and console output.

    Returns the root application logger.
    """
    # Ensure log directory exists
    log_dir = os.path.join(APP_TEMP_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(
        log_dir,
        f"inspectlog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    # Root logger for the app
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(level)

    # Prevent duplicate handlers on re-init
    if logger.handlers:
        return logger

    # Console handler (INFO+)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_fmt)

    # File handler (DEBUG+)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s:%(funcName)s:%(lineno)d — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_fmt)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logger.info("Logging initialized — log file: %s", log_file)
    return logger


def get_logger(module_name: str) -> logging.Logger:
    """Get a child logger for a specific module.

    Args:
        module_name: Name of the module (e.g., 'battery_reader').

    Returns:
        A child logger under the application root.
    """
    return logging.getLogger(f"{APP_NAME}.{module_name}")

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from phonebook.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    level_name = settings["log_level"].upper()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    if getattr(root_logger, "_phonebook_configured", False):
        root_logger.setLevel(level)
        return

    log_file = Path(settings["log_file"])
    if not log_file.is_absolute():
        log_file = Path(__file__).resolve().parents[1] / log_file
    log_file.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger._phonebook_configured = True  # type: ignore[attr-defined]

"""Logging setup that never leaks secrets."""
from __future__ import annotations

import logging
import re
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = _LOG_DIR / "govbid.log"

_SECRET_PATTERN = re.compile(r"(gsk_[A-Za-z0-9]+)")


class RedactingFilter(logging.Filter):
    """Strips anything that looks like a Groq API key from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _SECRET_PATTERN.sub("gsk_***REDACTED***", record.msg)
        return True


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.addFilter(RedactingFilter())

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    try:
        file_handler = logging.FileHandler(_LOG_FILE)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        pass

    return logger

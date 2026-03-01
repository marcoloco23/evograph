"""Logging configuration for EvoGraph API.

Supports two output formats:
- text: Human-readable format for development
- json: Structured JSON format for production log aggregators (ELK, Datadog, etc.)

Configured via LOG_LEVEL and LOG_FORMAT environment variables.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from evograph.settings import settings


class JSONFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def configure_logging() -> None:
    """Set up root logger based on application settings."""
    level = getattr(logging, settings.log_level.upper())

    if settings.log_format == "json":
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s %(name)s — %(message)s")
        )

    # Configure root logger
    root = logging.getLogger()
    root.setLevel(level)
    # Remove existing handlers to avoid duplicates on reloads
    root.handlers.clear()
    root.addHandler(handler)

    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

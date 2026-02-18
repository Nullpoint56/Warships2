"""Public engine logging API."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EngineLoggingConfig:
    """Engine logging pipeline configuration."""

    level_name: str = "INFO"
    console_format: str = "text"  # text|json
    file_path: str | None = None
    file_format: str = "json"  # text|json


class LoggerPort(Protocol):
    """Minimal logger surface for app/engine callers."""

    def debug(self, message: str, *args: object, **kwargs: object) -> None: ...

    def info(self, message: str, *args: object, **kwargs: object) -> None: ...

    def warning(self, message: str, *args: object, **kwargs: object) -> None: ...

    def error(self, message: str, *args: object, **kwargs: object) -> None: ...

    def exception(self, message: str, *args: object, **kwargs: object) -> None: ...


class JsonFormatter(logging.Formatter):
    """JSON formatter with extra-field preservation."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        standard = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
        }
        extras = {k: v for k, v in record.__dict__.items() if k not in standard}
        if extras:
            payload["fields"] = extras
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(config: EngineLoggingConfig) -> None:
    """Configure engine logging pipeline from config."""
    from engine.runtime.logging import configure_engine_logging

    configure_engine_logging(config)


def get_logger(name: str) -> LoggerPort:
    """Return namespaced logger from engine logging backend."""
    from engine.runtime.logging import get_engine_logger

    return get_engine_logger(name)

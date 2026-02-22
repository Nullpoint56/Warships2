"""Public engine logging API."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from engine.diagnostics.json_codec import dumps_text


@dataclass(frozen=True, slots=True)
class EngineLoggingConfig:
    """Engine logging pipeline configuration."""

    level_name: str = "INFO"
    console_format: str = "text"  # text|json
    file_path: str | None = None
    file_format: str = "json"  # text|json


class LoggerPort(Protocol):
    """Minimal logger surface for app/engine callers."""

    def debug(self, message: "LogValue", *args: "LogValue", **kwargs: "LogValue") -> None: ...

    def info(self, message: "LogValue", *args: "LogValue", **kwargs: "LogValue") -> None: ...

    def warning(self, message: "LogValue", *args: "LogValue", **kwargs: "LogValue") -> None: ...

    def error(self, message: "LogValue", *args: "LogValue", **kwargs: "LogValue") -> None: ...

    def exception(self, message: "LogValue", *args: "LogValue", **kwargs: "LogValue") -> None: ...


class LogValue(Protocol):
    """Opaque logging argument boundary contract."""


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
        return dumps_text(payload, compact=False)

"""Engine logging implementation."""

from __future__ import annotations

import json
import logging
import queue
from datetime import UTC, datetime
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path

from engine.api.logging import EngineLoggingConfig
from engine.runtime.debug_config import resolve_log_level_name

_QUEUE_LISTENER: QueueListener | None = None
RESERVED_LOGGER_NAMES: tuple[str, ...] = ("engine.network", "engine.audio")


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


def configure_engine_logging(config: EngineLoggingConfig) -> None:
    """Configure root logging with optional async file streaming."""
    global _QUEUE_LISTENER

    if _QUEUE_LISTENER is not None:
        _QUEUE_LISTENER.stop()
        _QUEUE_LISTENER = None

    level = getattr(logging, config.level_name.upper(), logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(_resolve_formatter(config.console_format))
    handlers: list[logging.Handler] = [console_handler]

    if config.file_path:
        file_path = Path(config.file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(file_path, mode="a", encoding="utf-8", delay=True)
        file_handler.setFormatter(_resolve_formatter(config.file_format))
        handlers.append(file_handler)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    if len(handlers) == 1:
        root.addHandler(handlers[0])
        return

    log_queue: queue.SimpleQueue[logging.LogRecord] = queue.SimpleQueue()
    root.addHandler(QueueHandler(log_queue))
    _QUEUE_LISTENER = QueueListener(log_queue, *handlers, respect_handler_level=True)
    _QUEUE_LISTENER.start()


def setup_engine_logging() -> None:
    """Configure minimal engine logging if no handlers are present."""
    root = logging.getLogger()
    if root.handlers:
        return
    configure_engine_logging(
        EngineLoggingConfig(
            level_name=resolve_log_level_name(default="INFO"),
            console_format="text",
            file_path=None,
            file_format="json",
        )
    )


def get_engine_logger(name: str) -> logging.Logger:
    """Return namespaced logger instance."""
    return logging.getLogger(name)


def _resolve_formatter(kind: str) -> logging.Formatter:
    if kind.strip().lower() == "json":
        return JsonFormatter()
    return logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

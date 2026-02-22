"""Engine logging implementation."""

from __future__ import annotations

import logging
import queue
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path
from dataclasses import dataclass

from engine.api.logging import EngineLoggingConfig, JsonFormatter
from engine.runtime.debug_config import resolve_log_level_name


@dataclass(slots=True)
class _LoggingRuntimeState:
    queue_listener: QueueListener | None = None


_LOGGING_RUNTIME = _LoggingRuntimeState()
RESERVED_LOGGER_NAMES: tuple[str, ...] = ("engine.network", "engine.audio")


def configure_engine_logging(config: EngineLoggingConfig) -> None:
    """Configure root logging with optional async file streaming."""
    if _LOGGING_RUNTIME.queue_listener is not None:
        _LOGGING_RUNTIME.queue_listener.stop()
        _LOGGING_RUNTIME.queue_listener = None

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
    _LOGGING_RUNTIME.queue_listener = QueueListener(log_queue, *handlers, respect_handler_level=True)
    _LOGGING_RUNTIME.queue_listener.start()


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

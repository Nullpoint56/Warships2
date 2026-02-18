"""Public engine logging API."""

from __future__ import annotations

from dataclasses import dataclass
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


def configure_logging(config: EngineLoggingConfig) -> None:
    """Configure engine logging pipeline from config."""
    from engine.runtime.logging import configure_engine_logging

    configure_engine_logging(config)


def get_logger(name: str) -> LoggerPort:
    """Return namespaced logger from engine logging backend."""
    from engine.runtime.logging import get_engine_logger

    return get_engine_logger(name)


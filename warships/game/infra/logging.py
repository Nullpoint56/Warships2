"""App-level logging policy over engine logging API."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from engine.api.logging import EngineLoggingConfig, configure_logging
from engine.runtime.logging import JsonFormatter
from warships.game.infra.app_data import resolve_logs_dir


def setup_logging() -> None:
    """Configure application logging via engine logging API."""
    level_name = os.getenv("WARSHIPS_LOG_LEVEL", os.getenv("LOG_LEVEL", "INFO")).upper()
    console_format = os.getenv("LOG_FORMAT", "json").lower()
    file_path = _resolve_run_log_file_path()
    configure_logging(
        EngineLoggingConfig(
            level_name=level_name,
            console_format=console_format,
            file_path=file_path,
            file_format="json",
        )
    )
    logging.getLogger(__name__).info("logging_file=%s", file_path)


def _resolve_run_log_file_path() -> str:
    configured = os.getenv("WARSHIPS_LOG_DIR", "").strip()
    base_dir = Path(configured) if configured else resolve_logs_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    return str(base_dir / f"warships_run_{stamp}.jsonl")

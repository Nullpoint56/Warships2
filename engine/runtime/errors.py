"""Shared runtime exception policy helpers."""

from __future__ import annotations

import logging
from typing import TypeAlias

# Explicitly bounded fallback set for runtime/backend compatibility paths.
RecoverableRuntimeErrors: TypeAlias = tuple[type[BaseException], ...]
RECOVERABLE_RUNTIME_ERRORS: RecoverableRuntimeErrors = (
    RuntimeError,
    OSError,
    ValueError,
    TypeError,
    AttributeError,
    ImportError,
)


def log_recoverable(
    logger: logging.Logger,
    message: str,
    *,
    level: int = logging.DEBUG,
) -> None:
    """Emit structured observability for tolerated recoverable exceptions."""
    logger.log(level, message, exc_info=True)

"""Structured diagnostics event schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class DiagnosticEvent:
    """Single structured diagnostics event."""

    ts_utc: str
    tick: int
    category: str
    name: str
    level: str = "info"
    value: float | int | str | bool | dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def utc_now_iso() -> str:
    """Return an RFC3339-like UTC timestamp with milliseconds."""
    now = datetime.now(tz=UTC)
    return now.isoformat(timespec="milliseconds")

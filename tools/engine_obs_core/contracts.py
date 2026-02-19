from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.diagnostics.schema import (
    DIAG_PROFILING_SCHEMA_VERSION,
    DIAG_REPLAY_SESSION_SCHEMA_VERSION,
    ENGINE_CRASH_BUNDLE_SCHEMA_VERSION,
)


@dataclass(frozen=True)
class EventRecord:
    ts_utc: str
    tick: int
    category: str
    name: str
    level: str
    value: float | int | str | bool | dict[str, Any] | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FramePoint:
    tick: int
    frame_ms: float
    render_ms: float
    fps_rolling: float


@dataclass(frozen=True)
class SpanRecord:
    tick: int
    category: str
    name: str
    start_s: float
    end_s: float
    duration_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReplayCommandRecord:
    tick: int
    type: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReplayCheckpointRecord:
    tick: int
    hash: str


@dataclass(frozen=True)
class CrashBundleRecord:
    schema_version: str
    captured_at_utc: str
    tick: int
    reason: str | None
    exception: dict[str, Any] | None
    runtime: dict[str, Any] = field(default_factory=dict)
    recent_events: list[dict[str, Any]] = field(default_factory=list)
    profiling: dict[str, Any] = field(default_factory=dict)
    replay: dict[str, Any] = field(default_factory=dict)


def has_schema_version(payload: dict[str, Any], expected: str) -> bool:
    return str(payload.get("schema_version", "")) == expected


def is_profiling_payload(payload: dict[str, Any]) -> bool:
    return has_schema_version(payload, DIAG_PROFILING_SCHEMA_VERSION)


def is_replay_payload(payload: dict[str, Any]) -> bool:
    return has_schema_version(payload, DIAG_REPLAY_SESSION_SCHEMA_VERSION)


def is_crash_bundle_payload(payload: dict[str, Any]) -> bool:
    return has_schema_version(payload, ENGINE_CRASH_BUNDLE_SCHEMA_VERSION)

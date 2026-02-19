from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from tools.engine_obs_core.contracts import (
    CrashBundleRecord,
    EventRecord,
    FramePoint,
    ReplayCheckpointRecord,
    ReplayCommandRecord,
    SpanRecord,
)


@dataclass(frozen=True)
class SessionRef:
    id: str
    root: Path
    run_log: Path | None
    ui_log: Path | None


@dataclass(frozen=True)
class TimeWindow:
    start_ts_utc: str | None
    end_ts_utc: str | None


@dataclass(frozen=True)
class MetricsSnapshot:
    frame_points: list[FramePoint]


@dataclass(frozen=True)
class ReplaySession:
    commands: list[ReplayCommandRecord]
    checkpoints: list[ReplayCheckpointRecord]


class ObsSource(Protocol):
    def list_sessions(self) -> list[SessionRef]: ...

    def load_events(
        self, session: SessionRef, window: TimeWindow | None = None
    ) -> list[EventRecord]: ...

    def load_metrics(self, session: SessionRef) -> MetricsSnapshot: ...

    def load_spans(self, session: SessionRef, limit: int) -> list[SpanRecord]: ...

    def load_replay(self, session: SessionRef) -> ReplaySession: ...

    def load_crash(self, session: SessionRef) -> CrashBundleRecord | None: ...

    def export_report(self, report: dict, path: Path) -> Path: ...

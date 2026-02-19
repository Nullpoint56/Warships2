"""Session inspector state container."""

from __future__ import annotations

from dataclasses import dataclass, field

from tools.engine_obs_core.contracts import CrashBundleRecord, EventRecord, SpanRecord
from tools.engine_obs_core.datasource.base import MetricsSnapshot, ReplaySession, SessionRef


@dataclass
class InspectorState:
    sessions: list[SessionRef] = field(default_factory=list)
    selected_session: SessionRef | None = None
    events: list[EventRecord] = field(default_factory=list)
    spans: list[SpanRecord] = field(default_factory=list)
    metrics: MetricsSnapshot = field(default_factory=lambda: MetricsSnapshot(frame_points=[]))
    replay: ReplaySession = field(
        default_factory=lambda: ReplaySession(commands=[], checkpoints=[])
    )
    crash: CrashBundleRecord | None = None

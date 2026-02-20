from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from engine.api.debug import (
    get_diagnostics_snapshot,
    get_metrics_snapshot,
    get_profiling_snapshot,
)
from tools.engine_obs_core.contracts import CrashBundleRecord, EventRecord, FramePoint, SpanRecord
from tools.engine_obs_core.datasource.base import (
    MetricsSnapshot,
    ObsSource,
    ReplaySession,
    SessionRef,
    TimeWindow,
)
from tools.engine_obs_core.datasource.file_source import FileObsSource


@dataclass(frozen=True)
class LiveSnapshot:
    polled_at_utc: str
    events: list[EventRecord]
    frame_points: list[FramePoint]
    spans: list[SpanRecord]
    rolling_frame_ms: float
    rolling_fps: float
    rolling_render_ms: float
    max_frame_ms: float
    resize_count: int


class LiveObsSource(FileObsSource, ObsSource):
    """Live diagnostics source built on top of the engine debug API."""

    def __init__(
        self,
        root: Path,
        *,
        host_provider: Callable[[], Any] | None = None,
        remote_url: str | None = None,
    ) -> None:
        super().__init__(root)
        self._host_provider = host_provider
        self._remote_url = (remote_url or "").rstrip("/")
        self._last_snapshot = LiveSnapshot(
            polled_at_utc="",
            events=[],
            frame_points=[],
            spans=[],
            rolling_frame_ms=0.0,
            rolling_fps=0.0,
            rolling_render_ms=0.0,
            max_frame_ms=0.0,
            resize_count=0,
        )
        self._poll_count = 0
        self._remote_snapshot_limit = _env_int("ENGINE_MONITOR_REMOTE_SNAPSHOT_LIMIT", 1200)
        self._remote_profiling_limit = _env_int("ENGINE_MONITOR_REMOTE_PROFILING_LIMIT", 600)
        self._remote_heavy_poll_every = _env_int("ENGINE_MONITOR_REMOTE_HEAVY_POLL_EVERY", 4)

    def poll(self, *, event_limit: int = 2_000, span_limit: int = 1_000) -> LiveSnapshot:
        host = self._host_provider() if callable(self._host_provider) else None
        if host is None and self._remote_url:
            remote_snapshot = self._poll_remote(event_limit=event_limit, span_limit=span_limit)
            if remote_snapshot is not None:
                self._last_snapshot = remote_snapshot
                return self._last_snapshot
        if host is None:
            return self._last_snapshot

        snapshot = get_diagnostics_snapshot(host, limit=max(1, int(event_limit)))
        metrics = get_metrics_snapshot(host)
        profiling = get_profiling_snapshot(host, limit=max(1, int(span_limit)))
        events = [
            EventRecord(
                ts_utc=str(item.get("ts_utc", "")),
                tick=int(item.get("tick", 0)),
                category=str(item.get("category", "")),
                name=str(item.get("name", "")),
                level=str(item.get("level", "info")),
                value=item.get("value"),
                metadata=dict(item.get("metadata", {}) or {}),
            )
            for item in snapshot.events
            if isinstance(item, dict)
        ]
        spans = [
            SpanRecord(
                tick=int(item.get("tick", 0)),
                category=str(item.get("category", "")),
                name=str(item.get("name", "")),
                start_s=float(item.get("start_s", 0.0)),
                end_s=float(item.get("end_s", 0.0)),
                duration_ms=float(item.get("duration_ms", 0.0)),
                metadata=dict(item.get("metadata", {}) or {}),
            )
            for item in profiling.spans
            if isinstance(item, dict)
        ]
        frame_points = self._derive_frame_points(events)
        self._last_snapshot = LiveSnapshot(
            polled_at_utc=datetime.now(tz=UTC).isoformat(timespec="milliseconds"),
            events=events,
            frame_points=frame_points,
            spans=spans,
            rolling_frame_ms=float(metrics.rolling_frame_ms),
            rolling_fps=float(metrics.rolling_fps),
            rolling_render_ms=float(metrics.rolling_render_ms),
            max_frame_ms=float(metrics.max_frame_ms),
            resize_count=int(metrics.resize_count),
        )
        return self._last_snapshot

    def _poll_remote(self, *, event_limit: int, span_limit: int) -> LiveSnapshot | None:
        self._poll_count += 1
        has_cached_payload = bool(self._last_snapshot.events) and bool(self._last_snapshot.spans)
        poll_heavy = (self._poll_count % max(1, self._remote_heavy_poll_every)) == 0
        if not has_cached_payload:
            poll_heavy = True
        try:
            snapshot = self._fetch_json(
                f"{self._remote_url}/snapshot?limit={max(100, min(50000, self._remote_snapshot_limit))}"
            ) if poll_heavy else {"events": [e.__dict__ for e in self._last_snapshot.events]}
            metrics = self._fetch_json(f"{self._remote_url}/metrics")
            profiling = self._fetch_json(
                f"{self._remote_url}/profiling?limit={max(100, min(50000, self._remote_profiling_limit))}"
            ) if poll_heavy else {"spans": [s.__dict__ for s in self._last_snapshot.spans]}
        except OSError, URLError, ValueError:
            return None
        events = [
            EventRecord(
                ts_utc=str(item.get("ts_utc", "")),
                tick=int(item.get("tick", 0)),
                category=str(item.get("category", "")),
                name=str(item.get("name", "")),
                level=str(item.get("level", "info")),
                value=item.get("value"),
                metadata=dict(item.get("metadata", {}) or {}),
            )
            for item in list(snapshot.get("events", []))[-max(1, int(event_limit)) :]
            if isinstance(item, dict)
        ]
        spans = [
            SpanRecord(
                tick=int(item.get("tick", 0)),
                category=str(item.get("category", "")),
                name=str(item.get("name", "")),
                start_s=float(item.get("start_s", 0.0)),
                end_s=float(item.get("end_s", 0.0)),
                duration_ms=float(item.get("duration_ms", 0.0)),
                metadata=dict(item.get("metadata", {}) or {}),
            )
            for item in list(profiling.get("spans", []))[-max(1, int(span_limit)) :]
            if isinstance(item, dict)
        ]
        return LiveSnapshot(
            polled_at_utc=datetime.now(tz=UTC).isoformat(timespec="milliseconds"),
            events=events,
            frame_points=self._derive_frame_points(events),
            spans=spans,
            rolling_frame_ms=float(metrics.get("rolling_frame_ms", 0.0)),
            rolling_fps=float(metrics.get("rolling_fps", 0.0)),
            rolling_render_ms=float(metrics.get("rolling_render_ms", 0.0)),
            max_frame_ms=float(metrics.get("max_frame_ms", 0.0)),
            resize_count=int(metrics.get("resize_count", 0)),
        )

    @staticmethod
    def _fetch_json(url: str) -> dict[str, Any]:
        with urlopen(url, timeout=1.0) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Remote payload is not a JSON object.")
        return payload

    def list_sessions(self) -> list[SessionRef]:
        return [SessionRef(id="live", root=self._root, run_log=None, ui_log=None)]

    def load_events(
        self, session: SessionRef, window: TimeWindow | None = None
    ) -> list[EventRecord]:
        _ = session
        snap = self.poll()
        events = snap.events
        if window is None:
            return events
        return self._apply_window(events, window)

    def load_metrics(self, session: SessionRef) -> MetricsSnapshot:
        _ = session
        snap = self.poll()
        return MetricsSnapshot(frame_points=snap.frame_points)

    def load_spans(self, session: SessionRef, limit: int) -> list[SpanRecord]:
        _ = session
        snap = self.poll(span_limit=max(1, int(limit)))
        return snap.spans[-max(1, int(limit)) :]

    def load_replay(self, session: SessionRef) -> ReplaySession:
        _ = session
        return ReplaySession(commands=[], checkpoints=[])

    def load_crash(self, session: SessionRef) -> CrashBundleRecord | None:
        _ = session
        return None

    @staticmethod
    def _derive_frame_points(events: list[EventRecord]) -> list[FramePoint]:
        by_tick: dict[int, dict[str, float]] = {}
        for event in events:
            tick = int(event.tick)
            bucket = by_tick.setdefault(tick, {})
            if event.name == "frame.time_ms" and isinstance(event.value, (int, float)):
                bucket["frame_ms"] = float(event.value)
            elif event.name == "render.frame_ms" and isinstance(event.value, (int, float)):
                bucket["render_ms"] = float(event.value)

        out: list[FramePoint] = []
        for tick in sorted(by_tick):
            frame_ms = float(by_tick[tick].get("frame_ms", 0.0))
            render_ms = float(by_tick[tick].get("render_ms", 0.0))
            fps = (1000.0 / frame_ms) if frame_ms > 0.0 else 0.0
            out.append(
                FramePoint(
                    tick=tick,
                    frame_ms=frame_ms,
                    render_ms=render_ms,
                    fps_rolling=fps,
                )
            )
        return out


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return int(default)
    try:
        value = int(raw.strip())
    except ValueError:
        value = int(default)
    return max(1, value)

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from engine.api.debug import DebugSessionBundle, discover_debug_sessions, load_debug_session
from engine.diagnostics.schema import (
    DIAG_PROFILING_SCHEMA_VERSION,
    DIAG_REPLAY_SESSION_SCHEMA_VERSION,
    ENGINE_CRASH_BUNDLE_SCHEMA_VERSION,
)
from tools.engine_obs_core.contracts import (
    CrashBundleRecord,
    EventRecord,
    ReplayCheckpointRecord,
    ReplayCommandRecord,
    SpanRecord,
    is_crash_bundle_payload,
    is_profiling_payload,
    is_replay_payload,
)
from tools.engine_obs_core.datasource.base import (
    MetricsSnapshot,
    ObsSource,
    ReplaySession,
    SessionRef,
    TimeWindow,
)
from tools.engine_obs_core.export import export_json_report


def _parse_ts(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class FileObsSource(ObsSource):
    """File-backed diagnostics source using existing engine debug loaders."""

    def __init__(self, root: Path, *, recursive: bool = True) -> None:
        self._root = root
        self._recursive = recursive

    def list_sessions(self) -> list[SessionRef]:
        bundles = discover_debug_sessions(self._root, recursive=self._recursive)
        out: list[SessionRef] = []
        for idx, bundle in enumerate(bundles):
            out.append(
                SessionRef(
                    id=f"session-{idx}",
                    root=self._root,
                    run_log=bundle.run_log,
                    ui_log=bundle.ui_log,
                )
            )
        return out

    def load_events(
        self, session: SessionRef, window: TimeWindow | None = None
    ) -> list[EventRecord]:
        loaded = self._load_session(session)
        events: list[EventRecord] = []

        for record in loaded.run_records:
            ts_utc = str(record.get("ts", ""))
            logger = str(record.get("logger", "runlog"))
            level = str(record.get("level", "INFO")).lower()
            msg = str(record.get("msg", ""))
            tick = self._extract_tick(record)
            category = self._derive_category(logger, msg)
            name = self._derive_name(logger, msg)
            metadata = dict(record)
            for key in ("ts", "logger", "level", "msg"):
                metadata.pop(key, None)
            events.append(
                EventRecord(
                    ts_utc=ts_utc,
                    tick=tick,
                    category=category,
                    name=name,
                    level=level,
                    value=msg,
                    metadata=metadata,
                )
            )

        for frame in loaded.ui_frames:
            ts_utc = str(frame.get("ts_utc", ""))
            frame_seq = int(frame.get("frame_seq", 0))
            events.append(
                EventRecord(
                    ts_utc=ts_utc,
                    tick=frame_seq,
                    category="ui_diag",
                    name="ui.frame",
                    level="info" if not frame.get("anomalies") else "warning",
                    value={
                        "reasons": list(frame.get("reasons", [])),
                        "anomalies": list(frame.get("anomalies", [])),
                    },
                    metadata=dict(frame),
                )
            )

        events.sort(key=lambda item: (_parse_ts(item.ts_utc) or datetime.min, item.tick))
        return self._apply_window(events, window)

    def load_metrics(self, session: SessionRef) -> MetricsSnapshot:
        loaded = self._load_session(session)
        points = []
        previous_ts: datetime | None = None
        for frame in loaded.ui_frames:
            ts = _parse_ts(frame.get("ts_utc"))
            if ts is None:
                continue
            tick = int(frame.get("frame_seq", 0))
            if previous_ts is None:
                previous_ts = ts
                continue
            frame_ms = max(0.0, (ts - previous_ts).total_seconds() * 1000.0)
            previous_ts = ts
            timing = frame.get("timing") if isinstance(frame.get("timing"), dict) else {}
            render_ms_raw = timing.get("apply_to_frame_ms")
            render_ms = float(render_ms_raw) if isinstance(render_ms_raw, (int, float)) else 0.0
            fps = (1000.0 / frame_ms) if frame_ms > 0.0 else 0.0
            points.append(
                {
                    "tick": tick,
                    "frame_ms": frame_ms,
                    "render_ms": render_ms,
                    "fps_rolling": fps,
                }
            )
        from tools.engine_obs_core.contracts import FramePoint

        return MetricsSnapshot(frame_points=[FramePoint(**p) for p in points])

    def load_spans(self, session: SessionRef, limit: int) -> list[SpanRecord]:
        payload = self._find_latest_payload(
            session,
            schema=DIAG_PROFILING_SCHEMA_VERSION,
            subdir="profiling",
        )
        if payload is None or not is_profiling_payload(payload):
            return []
        spans_raw = payload.get("spans", [])
        if not isinstance(spans_raw, list):
            return []
        spans: list[SpanRecord] = []
        for item in spans_raw[-max(1, int(limit)) :]:
            if not isinstance(item, dict):
                continue
            spans.append(
                SpanRecord(
                    tick=int(item.get("tick", 0)),
                    category=str(item.get("category", "")),
                    name=str(item.get("name", "")),
                    start_s=float(item.get("start_s", 0.0)),
                    end_s=float(item.get("end_s", 0.0)),
                    duration_ms=float(item.get("duration_ms", 0.0)),
                    metadata=dict(item.get("metadata", {}) or {}),
                )
            )
        return spans

    def load_replay(self, session: SessionRef) -> ReplaySession:
        payload = self._find_latest_payload(
            session,
            schema=DIAG_REPLAY_SESSION_SCHEMA_VERSION,
            subdir="replay",
        )
        if payload is None or not is_replay_payload(payload):
            return ReplaySession(commands=[], checkpoints=[])

        commands_raw = payload.get("commands", [])
        checkpoints_raw = payload.get("state_hashes", [])
        commands: list[ReplayCommandRecord] = []
        checkpoints: list[ReplayCheckpointRecord] = []

        if isinstance(commands_raw, list):
            for item in commands_raw:
                if not isinstance(item, dict):
                    continue
                commands.append(
                    ReplayCommandRecord(
                        tick=int(item.get("tick", 0)),
                        type=str(item.get("type", "")),
                        payload=dict(item.get("payload", {}) or {}),
                    )
                )
        if isinstance(checkpoints_raw, list):
            for item in checkpoints_raw:
                if not isinstance(item, dict):
                    continue
                checkpoints.append(
                    ReplayCheckpointRecord(
                        tick=int(item.get("tick", 0)),
                        hash=str(item.get("hash", "")),
                    )
                )
        return ReplaySession(commands=commands, checkpoints=checkpoints)

    def load_crash(self, session: SessionRef) -> CrashBundleRecord | None:
        payload = self._find_latest_payload(
            session,
            schema=ENGINE_CRASH_BUNDLE_SCHEMA_VERSION,
            subdir="crash",
        )
        if payload is None or not is_crash_bundle_payload(payload):
            return None
        return CrashBundleRecord(
            schema_version=str(payload.get("schema_version", "")),
            captured_at_utc=str(payload.get("captured_at_utc", "")),
            tick=int(payload.get("tick", 0)),
            reason=(str(payload.get("reason")) if payload.get("reason") is not None else None),
            exception=(
                dict(payload.get("exception"))
                if isinstance(payload.get("exception"), dict)
                else None
            ),
            runtime=dict(payload.get("runtime", {}) or {}),
            recent_events=list(payload.get("recent_events", []) or []),
            profiling=dict(payload.get("profiling", {}) or {}),
            replay=dict(payload.get("replay", {}) or {}),
        )

    def export_report(self, report: dict, path: Path) -> Path:
        return export_json_report(report, path)

    def _load_session(self, session: SessionRef):
        bundle = DebugSessionBundle(
            run_log=session.run_log,
            ui_log=session.ui_log,
            run_stamp=None,
            ui_stamp=None,
        )
        return load_debug_session(bundle)

    def _apply_window(
        self, events: list[EventRecord], window: TimeWindow | None
    ) -> list[EventRecord]:
        if window is None:
            return events
        start = _parse_ts(window.start_ts_utc)
        end = _parse_ts(window.end_ts_utc)
        out: list[EventRecord] = []
        for event in events:
            ts = _parse_ts(event.ts_utc)
            if ts is None:
                continue
            if start is not None and ts < start:
                continue
            if end is not None and ts > end:
                continue
            out.append(event)
        return out

    @staticmethod
    def _extract_tick(record: dict[str, Any]) -> int:
        for key in ("frame", "frame_index", "tick", "frame_seq"):
            value = record.get(key)
            if isinstance(value, int):
                return value
        return 0

    @staticmethod
    def _derive_category(logger: str, msg: str) -> str:
        value = logger.lower()
        text = msg.lower()
        if "render" in value or "ui_diag" in text:
            return "render"
        if "input" in value or "pointer" in text:
            return "input"
        if "profil" in value:
            return "perf"
        if "runtime" in value:
            return "frame"
        return "log"

    @staticmethod
    def _derive_name(logger: str, msg: str) -> str:
        if logger:
            return logger
        text = msg.strip()
        if not text:
            return "log"
        return text.split(" ", 1)[0]

    def _find_latest_payload(
        self, session: SessionRef, *, schema: str, subdir: str
    ) -> dict[str, Any] | None:
        candidates: list[Path] = []
        if session.root.exists():
            candidates.append(session.root / subdir)
            candidates.append(session.root.parent / subdir)
            candidates.append(session.root / "tools" / "data" / subdir)
            # backward-compatible alternate folder naming
            if subdir == "profiling":
                candidates.append(session.root / "profiles")
                candidates.append(session.root.parent / "profiles")
                candidates.append(session.root / "tools" / "data" / "profiles")
        candidates.append(self._root / subdir)
        candidates.append(self._root.parent / subdir)
        candidates.append(self._root / "tools" / "data" / subdir)
        if subdir == "profiling":
            candidates.append(self._root / "profiles")
            candidates.append(self._root.parent / "profiles")
            candidates.append(self._root / "tools" / "data" / "profiles")

        json_paths: list[Path] = []
        for base in candidates:
            if not base.exists() or not base.is_dir():
                continue
            json_paths.extend(base.glob("*.json"))
        json_paths.sort(key=lambda path: path.stat().st_mtime, reverse=True)

        for path in json_paths:
            payload = self._safe_load_json(path)
            if payload is None:
                continue
            if str(payload.get("schema_version", "")) == schema:
                return payload
        return None

    @staticmethod
    def _safe_load_json(path: Path) -> dict[str, Any] | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        return payload if isinstance(payload, dict) else None

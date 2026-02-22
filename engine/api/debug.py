"""Engine debug/observability API exposed to tools."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from engine.diagnostics import (
    DIAG_METRICS_SCHEMA_VERSION,
    DIAG_PROFILING_SCHEMA_VERSION,
    DIAG_REPLAY_MANIFEST_SCHEMA_VERSION,
    DIAG_REPLAY_SESSION_SCHEMA_VERSION,
    DIAG_REPLAY_VALIDATION_SCHEMA_VERSION,
    DIAG_SNAPSHOT_SCHEMA_VERSION,
)


@dataclass(frozen=True)
class DebugSessionBundle:
    run_log: Path | None
    ui_log: Path | None
    run_stamp: datetime | None
    ui_stamp: datetime | None


@dataclass(frozen=True)
class DebugLoadedSession:
    bundle: DebugSessionBundle
    run_records: list[dict[str, object]]
    ui_frames: list[dict[str, object]]
    summary: "SummaryView"


@dataclass(frozen=True)
class DiagnosticsSnapshot:
    schema_version: str
    events: list[dict[str, object]]


@dataclass(frozen=True)
class DiagnosticsMetricsView:
    schema_version: str
    frame_count: int
    rolling_frame_ms: float
    rolling_fps: float
    max_frame_ms: float
    resize_count: int
    resize_event_to_apply_p95_ms: float
    resize_apply_to_frame_p95_ms: float
    rolling_render_ms: float
    resize_burst_count: int
    resize_coalesced_total: int
    resize_redraw_skipped_total: int
    acquire_failures_total: int
    present_failures_total: int
    recovery_backoff_events_total: int
    adaptive_present_mode_switches_total: int


@dataclass(frozen=True)
class DiagnosticsProfilingView:
    schema_version: str
    mode: str
    span_count: int
    top_spans_ms: list[tuple[str, float]]
    spans: list[dict[str, object]]


@dataclass(frozen=True)
class DiagnosticsReplayManifestView:
    schema_version: str
    replay_version: int
    seed: int | None
    build: dict[str, object]
    command_count: int
    first_tick: int
    last_tick: int


@dataclass(frozen=True)
class DiagnosticsReplaySnapshotView:
    schema_version: str
    manifest: dict[str, object]
    commands: list[dict[str, object]]
    state_hashes: list[dict[str, object]]


@dataclass(frozen=True)
class ReplayValidationView:
    schema_version: str
    passed: bool
    total_ticks: int
    commands_applied: int
    checkpoint_count: int
    mismatches: list[dict[str, object]]


class SummaryView(Protocol):
    """Opaque summary payload contract for debug session reports."""


class HostLike(Protocol):
    """Opaque host boundary contract for diagnostics projections."""


class ReplayApplyCommand(Protocol):
    """Replay command application callback contract."""

    def __call__(self, command: dict[str, object]) -> None: ...


class ReplayStep(Protocol):
    """Replay simulation step callback contract."""

    def __call__(self, delta_seconds: float) -> None: ...


def discover_debug_sessions(log_dir: Path, *, recursive: bool = False) -> list[DebugSessionBundle]:
    from engine.diagnostics import observability

    bundles = observability.discover_session_bundles(log_dir, recursive=recursive)
    return [
        DebugSessionBundle(
            run_log=b.run_log,
            ui_log=b.ui_log,
            run_stamp=b.run_stamp,
            ui_stamp=b.ui_stamp,
        )
        for b in bundles
    ]


def load_debug_session(bundle: DebugSessionBundle) -> DebugLoadedSession:
    from engine.diagnostics import observability

    runtime_bundle = observability.SessionBundle(
        run_log=bundle.run_log,
        ui_log=bundle.ui_log,
        run_stamp=bundle.run_stamp,
        ui_stamp=bundle.ui_stamp,
    )
    loaded = observability.load_session(runtime_bundle)
    return DebugLoadedSession(
        bundle=DebugSessionBundle(
            run_log=loaded.bundle.run_log,
            ui_log=loaded.bundle.ui_log,
            run_stamp=loaded.bundle.run_stamp,
            ui_stamp=loaded.bundle.ui_stamp,
        ),
        run_records=loaded.run_records,
        ui_frames=loaded.ui_frames,
        summary=loaded.summary,
    )


def get_diagnostics_snapshot(
    host: HostLike,
    *,
    limit: int | None = None,
    category: str | None = None,
    name: str | None = None,
) -> DiagnosticsSnapshot:
    """Return a stable diagnostics payload for tools from a host-like object."""
    hub = getattr(host, "diagnostics_hub", None)
    if hub is None or not hasattr(hub, "snapshot"):
        return DiagnosticsSnapshot(schema_version=DIAG_SNAPSHOT_SCHEMA_VERSION, events=[])
    raw_events = hub.snapshot(limit=limit, category=category, name=name)
    events = [
        {
            "ts_utc": event.ts_utc,
            "tick": int(event.tick),
            "category": event.category,
            "name": event.name,
            "level": event.level,
            "value": event.value,
            "metadata": dict(event.metadata),
        }
        for event in raw_events
    ]
    return DiagnosticsSnapshot(schema_version=DIAG_SNAPSHOT_SCHEMA_VERSION, events=events)


def get_metrics_snapshot(host: HostLike) -> DiagnosticsMetricsView:
    """Return aggregated diagnostics metrics from a host-like object."""
    snapshot = getattr(host, "diagnostics_metrics_snapshot", None)
    if snapshot is None:
        return DiagnosticsMetricsView(
            schema_version=DIAG_METRICS_SCHEMA_VERSION,
            frame_count=0,
            rolling_frame_ms=0.0,
            rolling_fps=0.0,
            max_frame_ms=0.0,
            resize_count=0,
            resize_event_to_apply_p95_ms=0.0,
            resize_apply_to_frame_p95_ms=0.0,
            rolling_render_ms=0.0,
            resize_burst_count=0,
            resize_coalesced_total=0,
            resize_redraw_skipped_total=0,
            acquire_failures_total=0,
            present_failures_total=0,
            recovery_backoff_events_total=0,
            adaptive_present_mode_switches_total=0,
        )
    return DiagnosticsMetricsView(
        schema_version=DIAG_METRICS_SCHEMA_VERSION,
        frame_count=int(getattr(snapshot, "frame_count", 0)),
        rolling_frame_ms=float(getattr(snapshot, "rolling_frame_ms", 0.0)),
        rolling_fps=float(getattr(snapshot, "rolling_fps", 0.0)),
        max_frame_ms=float(getattr(snapshot, "max_frame_ms", 0.0)),
        resize_count=int(getattr(snapshot, "resize_count", 0)),
        resize_event_to_apply_p95_ms=float(getattr(snapshot, "resize_event_to_apply_p95_ms", 0.0)),
        resize_apply_to_frame_p95_ms=float(getattr(snapshot, "resize_apply_to_frame_p95_ms", 0.0)),
        rolling_render_ms=float(getattr(snapshot, "rolling_render_ms", 0.0)),
        resize_burst_count=int(getattr(snapshot, "resize_burst_count", 0)),
        resize_coalesced_total=int(getattr(snapshot, "resize_coalesced_total", 0)),
        resize_redraw_skipped_total=int(getattr(snapshot, "resize_redraw_skipped_total", 0)),
        acquire_failures_total=int(getattr(snapshot, "acquire_failures_total", 0)),
        present_failures_total=int(getattr(snapshot, "present_failures_total", 0)),
        recovery_backoff_events_total=int(
            getattr(snapshot, "recovery_backoff_events_total", 0)
        ),
        adaptive_present_mode_switches_total=int(
            getattr(snapshot, "adaptive_present_mode_switches_total", 0)
        ),
    )


def get_profiling_snapshot(host: HostLike, *, limit: int = 300) -> DiagnosticsProfilingView:
    """Return profiling spans and top offenders from a host-like object."""
    get_snapshot = getattr(host, "diagnostics_profiling_snapshot", None)
    if get_snapshot is None:
        return DiagnosticsProfilingView(
            schema_version=DIAG_PROFILING_SCHEMA_VERSION,
            mode="off",
            span_count=0,
            top_spans_ms=[],
            spans=[],
        )
    snapshot = get_snapshot
    spans_raw = list(getattr(snapshot, "spans", []))
    if limit > 0:
        spans_raw = spans_raw[-int(limit) :]
    spans = [
        {
            "tick": int(getattr(span, "tick", 0)),
            "category": str(getattr(span, "category", "")),
            "name": str(getattr(span, "name", "")),
            "start_s": float(getattr(span, "start_s", 0.0)),
            "end_s": float(getattr(span, "end_s", 0.0)),
            "duration_ms": float(getattr(span, "duration_ms", 0.0)),
            "metadata": dict(getattr(span, "metadata", {}) or {}),
        }
        for span in spans_raw
    ]
    top_raw = list(getattr(snapshot, "top_spans_ms", []))
    top: list[tuple[str, float]] = []
    for item in top_raw:
        if not (isinstance(item, tuple) or isinstance(item, list)) or len(item) != 2:
            continue
        top.append((str(item[0]), float(item[1])))
    return DiagnosticsProfilingView(
        schema_version=DIAG_PROFILING_SCHEMA_VERSION,
        mode=str(getattr(snapshot, "mode", "off")),
        span_count=int(getattr(snapshot, "span_count", len(spans))),
        top_spans_ms=top,
        spans=spans,
    )


def export_profiling_snapshot(host: HostLike, *, path: str) -> str | None:
    """Export profiling snapshot to JSON path via host diagnostics profiler."""
    exporter = getattr(host, "export_diagnostics_profiling", None)
    if not callable(exporter):
        return None
    return str(exporter(path=path))


def export_crash_bundle(host: HostLike, *, path: str) -> str | None:
    """Export a crash-style diagnostics bundle at the requested path."""
    exporter = getattr(host, "export_diagnostics_crash_bundle", None)
    if not callable(exporter):
        return None
    return str(exporter(path=path))


def get_replay_manifest(host: HostLike) -> DiagnosticsReplayManifestView:
    """Return replay manifest from host recorder when available."""
    manifest = getattr(host, "diagnostics_replay_manifest", None)
    if manifest is None:
        return DiagnosticsReplayManifestView(
            schema_version=DIAG_REPLAY_MANIFEST_SCHEMA_VERSION,
            replay_version=1,
            seed=None,
            build={},
            command_count=0,
            first_tick=0,
            last_tick=0,
        )
    return DiagnosticsReplayManifestView(
        schema_version=str(
            getattr(manifest, "schema_version", DIAG_REPLAY_MANIFEST_SCHEMA_VERSION)
        ),
        replay_version=int(getattr(manifest, "replay_version", 1)),
        seed=getattr(manifest, "seed", None),
        build=dict(getattr(manifest, "build", {}) or {}),
        command_count=int(getattr(manifest, "command_count", 0)),
        first_tick=int(getattr(manifest, "first_tick", 0)),
        last_tick=int(getattr(manifest, "last_tick", 0)),
    )


def export_replay_session(host: HostLike, *, path: str) -> str | None:
    """Export replay capture session via host recorder."""
    exporter = getattr(host, "export_diagnostics_replay", None)
    if not callable(exporter):
        return None
    return str(exporter(path=path))


def get_replay_snapshot(host: HostLike, *, limit: int = 5_000) -> DiagnosticsReplaySnapshotView:
    """Return captured replay session payload from host recorder."""
    snapshot = getattr(host, "diagnostics_replay_snapshot", None)
    if snapshot is None:
        return DiagnosticsReplaySnapshotView(
            schema_version=DIAG_REPLAY_SESSION_SCHEMA_VERSION,
            manifest={},
            commands=[],
            state_hashes=[],
        )
    payload = dict(snapshot)
    commands = list(payload.get("commands", []))
    if limit > 0:
        commands = commands[-int(limit) :]
    return DiagnosticsReplaySnapshotView(
        schema_version=str(payload.get("schema_version", DIAG_REPLAY_SESSION_SCHEMA_VERSION)),
        manifest=dict(payload.get("manifest", {}) or {}),
        commands=[dict(item) for item in commands if isinstance(item, dict)],
        state_hashes=[
            dict(item) for item in list(payload.get("state_hashes", [])) if isinstance(item, dict)
        ],
    )


def validate_replay_snapshot(
    replay_snapshot: dict[str, object],
    *,
    fixed_step_seconds: float,
    apply_command: ReplayApplyCommand,
    step: ReplayStep,
) -> ReplayValidationView:
    """Validate replay snapshot determinism with provided simulation callbacks."""
    from engine.diagnostics import FixedStepReplayRunner

    runner = FixedStepReplayRunner(fixed_step_seconds=fixed_step_seconds)
    result = runner.run(replay_snapshot, apply_command=apply_command, step=step)
    return ReplayValidationView(
        schema_version=DIAG_REPLAY_VALIDATION_SCHEMA_VERSION,
        passed=bool(result.passed),
        total_ticks=int(result.total_ticks),
        commands_applied=int(result.commands_applied),
        checkpoint_count=int(result.checkpoint_count),
        mismatches=[
            {
                "tick": int(mismatch.tick),
                "expected_hash": mismatch.expected_hash,
                "actual_hash": mismatch.actual_hash,
            }
            for mismatch in result.mismatches
        ],
    )

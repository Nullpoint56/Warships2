from __future__ import annotations

from engine.api.debug import (
    DiagnosticsMetricsView,
    DiagnosticsProfilingView,
    DiagnosticsReplayManifestView,
    DiagnosticsReplaySnapshotView,
    DiagnosticsSnapshot,
)
from engine.diagnostics import (
    DIAG_METRICS_SCHEMA_VERSION,
    DIAG_PROFILING_SCHEMA_VERSION,
    DIAG_REPLAY_MANIFEST_SCHEMA_VERSION,
    DIAG_REPLAY_SESSION_SCHEMA_VERSION,
    DIAG_SNAPSHOT_SCHEMA_VERSION,
    ENGINE_CRASH_BUNDLE_SCHEMA_VERSION,
)
from engine.diagnostics.crash import CrashBundleWriter
from engine.diagnostics.hub import DiagnosticHub


def test_schema_constants_remain_stable() -> None:
    assert DIAG_SNAPSHOT_SCHEMA_VERSION == "diag.snapshot.v1"
    assert DIAG_METRICS_SCHEMA_VERSION == "diag.metrics.v1"
    assert DIAG_PROFILING_SCHEMA_VERSION == "diag.profiling.v1"
    assert DIAG_REPLAY_MANIFEST_SCHEMA_VERSION == "diag.replay_manifest.v1"
    assert DIAG_REPLAY_SESSION_SCHEMA_VERSION == "diag.replay_session.v1"
    assert ENGINE_CRASH_BUNDLE_SCHEMA_VERSION == "engine.crash_bundle.v1"


def test_debug_view_types_expose_schema_version_field() -> None:
    snapshot = DiagnosticsSnapshot(schema_version=DIAG_SNAPSHOT_SCHEMA_VERSION, events=[])
    metrics = DiagnosticsMetricsView(
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
    profiling = DiagnosticsProfilingView(
        schema_version=DIAG_PROFILING_SCHEMA_VERSION,
        mode="off",
        span_count=0,
        top_spans_ms=[],
        spans=[],
    )
    manifest = DiagnosticsReplayManifestView(
        schema_version=DIAG_REPLAY_MANIFEST_SCHEMA_VERSION,
        replay_version=1,
        seed=None,
        build={},
        command_count=0,
        first_tick=0,
        last_tick=0,
    )
    replay = DiagnosticsReplaySnapshotView(
        schema_version=DIAG_REPLAY_SESSION_SCHEMA_VERSION,
        manifest={},
        commands=[],
        state_hashes=[],
    )
    assert snapshot.schema_version.endswith(".v1")
    assert metrics.schema_version.endswith(".v1")
    assert profiling.schema_version.endswith(".v1")
    assert manifest.schema_version.endswith(".v1")
    assert replay.schema_version.endswith(".v1")


def test_crash_bundle_uses_expected_schema_version(tmp_path) -> None:
    writer = CrashBundleWriter(enabled=True, output_dir=tmp_path, recent_events_limit=20)
    hub = DiagnosticHub(enabled=True)
    try:
        raise ValueError("x")
    except ValueError as exc:
        path = writer.capture_exception(exc, tick=1, diagnostics_hub=hub)
    assert path is not None
    payload = path.read_text(encoding="utf-8")
    assert ENGINE_CRASH_BUNDLE_SCHEMA_VERSION in payload

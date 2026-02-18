from __future__ import annotations

import json
from pathlib import Path

from engine.diagnostics import CrashBundleWriter, DiagnosticHub


def test_crash_bundle_writer_writes_structured_bundle(tmp_path: Path) -> None:
    hub = DiagnosticHub(enabled=True)
    hub.emit_fast(category="frame", name="frame.start", tick=1)
    writer = CrashBundleWriter(enabled=True, output_dir=tmp_path, recent_events_limit=50)

    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        bundle_path = writer.capture_exception(
            exc,
            tick=7,
            diagnostics_hub=hub,
            runtime_metadata={"engine_versions": {"pygfx": "x"}},
            profiling_snapshot={"schema": "frame_profile_v1"},
        )

    assert bundle_path is not None
    assert bundle_path.exists()
    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "engine.crash_bundle.v1"
    assert payload["tick"] == 7
    assert payload["exception"]["type"] == "RuntimeError"
    assert payload["recent_events"]


def test_crash_bundle_writer_writes_manual_snapshot_bundle(tmp_path: Path) -> None:
    hub = DiagnosticHub(enabled=True)
    hub.emit_fast(category="frame", name="frame.start", tick=3)
    writer = CrashBundleWriter(enabled=True, output_dir=tmp_path, recent_events_limit=50)

    bundle_path = writer.capture_snapshot(
        tick=11,
        diagnostics_hub=hub,
        reason="manual_export",
        runtime_metadata={"engine_versions": {"pygfx": "x"}},
    )

    assert bundle_path is not None
    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "engine.crash_bundle.v1"
    assert payload["tick"] == 11
    assert payload["reason"] == "manual_export"
    assert payload["exception"] is None
    assert payload["recent_events"]

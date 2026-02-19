from __future__ import annotations

from tools.engine_obs_core.contracts import CrashBundleRecord, EventRecord
from tools.engine_session_inspector.views.crash import build_crash_focus_text


def test_crash_focus_prefers_crash_bundle_payload() -> None:
    crash = CrashBundleRecord(
        schema_version="engine.crash_bundle.v1",
        captured_at_utc="2026-01-01T00:00:00",
        tick=42,
        reason="manual_export",
        exception={"type": "RuntimeError", "message": "boom"},
        runtime={"engine": "test"},
        recent_events=[],
        profiling={},
        replay={},
    )

    text = build_crash_focus_text(crash, events=[])

    assert "schema_version=engine.crash_bundle.v1" in text
    assert "tick=42" in text
    assert "reason=manual_export" in text


def test_crash_focus_fallback_uses_warning_error_events() -> None:
    events = [
        EventRecord(
            ts_utc="2026-01-01T00:00:00",
            tick=2,
            category="render",
            name="render.unhandled_exception",
            level="error",
            value="boom",
            metadata={},
        )
    ]

    text = build_crash_focus_text(None, events)

    assert "No crash bundle loaded." in text
    assert "warning_or_error_events=1" in text
    assert "render.unhandled_exception" in text

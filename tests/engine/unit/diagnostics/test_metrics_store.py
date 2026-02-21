from __future__ import annotations

from engine.diagnostics.event import DiagnosticEvent
from engine.diagnostics.metrics_store import DiagnosticsMetricsStore


def test_metrics_store_collects_frame_and_render_and_resize_metrics() -> None:
    store = DiagnosticsMetricsStore(window_size=10)
    store.ingest(
        DiagnosticEvent(
            ts_utc="2026-01-01T00:00:00.000+00:00",
            tick=1,
            category="frame",
            name="frame.time_ms",
            value=16.0,
        )
    )
    store.ingest(
        DiagnosticEvent(
            ts_utc="2026-01-01T00:00:00.001+00:00",
            tick=1,
            category="render",
            name="render.frame_ms",
            value=5.0,
        )
    )
    store.ingest(
        DiagnosticEvent(
            ts_utc="2026-01-01T00:00:00.002+00:00",
            tick=1,
            category="render",
            name="render.resize_event",
            value={"width": 100, "height": 100},
            metadata={"event_to_apply_ms": 0.3, "apply_to_frame_ms": 0.7},
        )
    )
    store.ingest(
        DiagnosticEvent(
            ts_utc="2026-01-01T00:00:00.003+00:00",
            tick=1,
            category="window",
            name="window.resize_burst",
            value={"resize_coalesced_total": 2, "resize_redraw_skipped_total": 1},
        )
    )
    store.ingest(
        DiagnosticEvent(
            ts_utc="2026-01-01T00:00:00.004+00:00",
            tick=1,
            category="render",
            name="render.profile_frame",
            value={
                "acquire_failures": 3,
                "present_failures": 4,
                "recovery_backoff_events": 2,
                "adaptive_present_mode_switches": 1,
            },
        )
    )

    snapshot = store.snapshot()

    assert snapshot.frame_count == 1
    assert snapshot.rolling_frame_ms == 16.0
    assert snapshot.rolling_render_ms == 5.0
    assert snapshot.resize_count == 1
    assert snapshot.resize_event_to_apply_p95_ms >= 0.3
    assert snapshot.resize_apply_to_frame_p95_ms >= 0.7
    assert snapshot.resize_burst_count == 1
    assert snapshot.resize_coalesced_total == 2
    assert snapshot.resize_redraw_skipped_total == 1
    assert snapshot.acquire_failures_total == 3
    assert snapshot.present_failures_total == 4
    assert snapshot.recovery_backoff_events_total == 2
    assert snapshot.adaptive_present_mode_switches_total == 1

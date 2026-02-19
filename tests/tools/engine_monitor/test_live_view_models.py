from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.engine_obs_core.contracts import EventRecord, FramePoint, SpanRecord
from tools.engine_obs_core.datasource.live_source import LiveSnapshot
from tools.engine_monitor.views.health import build_health_view_model
from tools.engine_monitor.views.hitches import build_hitch_rows
from tools.engine_monitor.views.render_resize import build_render_resize_model
from tools.engine_monitor.views.timeline import build_timeline_points


def _sample_snapshot() -> LiveSnapshot:
    events = [
        EventRecord(
            ts_utc="2026-01-01T00:00:00.000+00:00",
            tick=10,
            category="frame",
            name="frame.time_ms",
            level="info",
            value=28.0,
            metadata={},
        ),
        EventRecord(
            ts_utc="2026-01-01T00:00:00.000+00:00",
            tick=10,
            category="render",
            name="render.frame_ms",
            level="info",
            value=9.0,
            metadata={},
        ),
        EventRecord(
            ts_utc="2026-01-01T00:00:00.000+00:00",
            tick=10,
            category="scheduler",
            name="scheduler.queue_depth",
            level="info",
            value=3,
            metadata={},
        ),
        EventRecord(
            ts_utc="2026-01-01T00:00:00.010+00:00",
            tick=11,
            category="render",
            name="render.resize_event",
            level="info",
            value={"w": 1920, "h": 1080},
            metadata={},
        ),
        EventRecord(
            ts_utc="2026-01-01T00:00:00.011+00:00",
            tick=11,
            category="render",
            name="render.viewport_applied",
            level="info",
            value={"sx": 1.0},
            metadata={},
        ),
    ]
    points = [
        FramePoint(tick=10, frame_ms=28.0, render_ms=9.0, fps_rolling=35.7),
        FramePoint(tick=11, frame_ms=18.0, render_ms=7.0, fps_rolling=55.5),
    ]
    spans = [
        SpanRecord(
            tick=10,
            category="render",
            name="present",
            start_s=1.0,
            end_s=1.010,
            duration_ms=10.0,
            metadata={},
        )
    ]
    return LiveSnapshot(
        polled_at_utc="2026-01-01T00:00:01.000+00:00",
        events=events,
        frame_points=points,
        spans=spans,
        rolling_frame_ms=20.0,
        rolling_fps=50.0,
        rolling_render_ms=8.0,
        max_frame_ms=28.0,
        resize_count=1,
    )


def test_health_and_timeline_models() -> None:
    snapshot = _sample_snapshot()
    health = build_health_view_model(snapshot, hitch_threshold_ms=20.0)
    timeline = build_timeline_points(snapshot.events)

    assert health.fps > 0.0
    assert health.frame_ms_p95 >= health.frame_ms_mean
    assert len(health.alerts) >= 1
    assert len(timeline) >= 1
    assert timeline[0].tick == 10
    assert timeline[0].queue_depth == 3.0


def test_hitch_and_render_resize_models() -> None:
    snapshot = _sample_snapshot()
    hitches = build_hitch_rows(snapshot, threshold_ms=20.0)
    render_resize = build_render_resize_model(snapshot.events)

    assert len(hitches) == 1
    assert hitches[0].tick == 10
    assert render_resize.resize_events == 1
    assert render_resize.viewport_updates == 1
    assert render_resize.last_resize_value != "n/a"

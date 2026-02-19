from __future__ import annotations

import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.engine_obs_core.contracts import EventRecord, FramePoint, SpanRecord
from tools.engine_obs_core.datasource.live_source import LiveSnapshot
from tools.engine_monitor.views.health import build_health_view_model
from tools.engine_monitor.views.hitches import build_hitch_rows
from tools.engine_monitor.views.render_resize import build_render_resize_model
from tools.engine_monitor.views.timeline import build_timeline_points


def _big_snapshot() -> LiveSnapshot:
    events = []
    for idx in range(15_000):
        events.append(
            EventRecord(
                ts_utc=f"2026-01-01T00:00:{idx % 60:02d}.000+00:00",
                tick=idx,
                category="frame",
                name="frame.time_ms",
                level="info",
                value=float((idx % 30) + 8),
                metadata={},
            )
        )
        events.append(
            EventRecord(
                ts_utc=f"2026-01-01T00:00:{idx % 60:02d}.010+00:00",
                tick=idx,
                category="render",
                name="render.frame_ms",
                level="info",
                value=float((idx % 12) + 2),
                metadata={},
            )
        )
    spans = [
        SpanRecord(
            tick=idx,
            category="render",
            name="present",
            start_s=0.0,
            end_s=0.0,
            duration_ms=float((idx % 15) + 1),
            metadata={},
        )
        for idx in range(10_000)
    ]
    points = [
        FramePoint(
            tick=idx,
            frame_ms=float((idx % 30) + 8),
            render_ms=float((idx % 12) + 2),
            fps_rolling=60.0,
        )
        for idx in range(15_000)
    ]
    return LiveSnapshot(
        polled_at_utc="2026-01-01T00:00:00.000+00:00",
        events=events,
        frame_points=points,
        spans=spans,
        rolling_frame_ms=16.6,
        rolling_fps=60.0,
        rolling_render_ms=5.2,
        max_frame_ms=38.0,
        resize_count=2,
    )


def test_monitor_view_model_performance_budget() -> None:
    snapshot = _big_snapshot()
    start = perf_counter()
    health = build_health_view_model(snapshot, hitch_threshold_ms=25.0)
    timeline = build_timeline_points(snapshot.events)
    hitches = build_hitch_rows(snapshot, threshold_ms=25.0)
    render_resize = build_render_resize_model(snapshot.events)
    elapsed = perf_counter() - start

    assert health.fps > 0.0
    assert len(timeline) > 0
    assert len(hitches) > 0
    assert render_resize.resize_events == 0
    assert elapsed < 0.75

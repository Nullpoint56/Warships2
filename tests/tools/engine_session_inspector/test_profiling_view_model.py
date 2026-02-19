from __future__ import annotations

from tools.engine_obs_core.contracts import FramePoint, SpanRecord
from tools.engine_session_inspector.views.profiling import build_profiling_view_model


def _span(tick: int, category: str, name: str, duration_ms: float) -> SpanRecord:
    return SpanRecord(
        tick=tick,
        category=category,
        name=name,
        start_s=0.0,
        end_s=0.0,
        duration_ms=duration_ms,
        metadata={},
    )


def test_build_profiling_view_model_returns_rankings_timeline_and_hitches() -> None:
    spans = [
        _span(1, "host", "frame", 6.0),
        _span(2, "host", "frame", 7.0),
        _span(2, "render", "present", 5.0),
        _span(30, "module", "on_frame", 12.0),
    ]
    frames = [
        FramePoint(tick=1, frame_ms=16.0, render_ms=5.0, fps_rolling=60.0),
        FramePoint(tick=2, frame_ms=17.0, render_ms=6.0, fps_rolling=58.0),
        FramePoint(tick=30, frame_ms=40.0, render_ms=12.0, fps_rolling=25.0),
    ]

    model = build_profiling_view_model(spans, frames, top_n=3, hitch_threshold_ms=25.0)

    assert model.total_spans == 4
    assert len(model.top_total_rows) >= 1
    assert len(model.top_p95_rows) >= 1
    assert model.timeline_points
    assert model.hitch_correlations
    assert model.hitch_correlations[0].tick == 30


def test_build_profiling_view_model_handles_empty_inputs() -> None:
    model = build_profiling_view_model([], [])
    assert model.total_spans == 0
    assert model.top_total_rows == []
    assert model.top_p95_rows == []
    assert model.timeline_points == []
    assert model.hitch_correlations == []

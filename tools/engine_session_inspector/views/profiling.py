"""Profiling view helpers for session inspector."""

from __future__ import annotations

from dataclasses import dataclass

from tools.engine_obs_core.aggregations import detect_hitches, top_span_aggregates
from tools.engine_obs_core.contracts import FramePoint, SpanRecord
from tools.engine_obs_core.timeline import build_span_bucket_series


@dataclass(frozen=True)
class HitchCorrelation:
    tick: int
    frame_ms: float
    top_span_key: str
    top_span_total_ms: float


@dataclass(frozen=True)
class ProfilingViewModel:
    total_spans: int
    timeline_points: list[tuple[int, float]]
    frame_timeline_points: list[tuple[int, float]]
    render_timeline_points: list[tuple[int, float]]
    top_total_rows: list[tuple[str, int, float, float]]
    top_p95_rows: list[tuple[str, int, float, float]]
    hitch_correlations: list[HitchCorrelation]


def build_profiling_view_model(
    spans: list[SpanRecord],
    frame_points: list[FramePoint],
    *,
    top_n: int = 10,
    hitch_threshold_ms: float = 25.0,
    hitch_window_ticks: int = 4,
) -> ProfilingViewModel:
    top_total = top_span_aggregates(spans, top_n=top_n, sort_by="total_ms")
    top_p95 = top_span_aggregates(spans, top_n=top_n, sort_by="p95_ms")
    timeline = build_span_bucket_series(spans, bucket_size_ticks=10)
    frame_timeline_points = [
        (int(point.tick), float(point.frame_ms)) for point in frame_points if point.frame_ms > 0.0
    ]
    render_timeline_points = [
        (int(point.tick), float(point.render_ms)) for point in frame_points if point.render_ms > 0.0
    ]
    # Keep timeline chart useful even when structured spans are unavailable.
    if not timeline and frame_timeline_points:
        timeline = list(frame_timeline_points)

    top_total_rows = [(row.key, row.count, row.total_ms, row.p95_ms) for row in top_total]
    top_p95_rows = [(row.key, row.count, row.p95_ms, row.max_ms) for row in top_p95]

    hitch_dicts = [{"tick": point.tick, "frame_ms": point.frame_ms} for point in frame_points]
    hitches = detect_hitches(hitch_dicts, threshold_ms=hitch_threshold_ms)

    correlations: list[HitchCorrelation] = []
    for hitch in hitches:
        nearby = [
            span
            for span in spans
            if abs(int(span.tick) - int(hitch.tick)) <= max(0, int(hitch_window_ticks))
        ]
        if not nearby:
            correlations.append(
                HitchCorrelation(
                    tick=hitch.tick,
                    frame_ms=hitch.frame_ms,
                    top_span_key="n/a",
                    top_span_total_ms=0.0,
                )
            )
            continue
        top = top_span_aggregates(nearby, top_n=1, sort_by="total_ms")[0]
        correlations.append(
            HitchCorrelation(
                tick=hitch.tick,
                frame_ms=hitch.frame_ms,
                top_span_key=top.key,
                top_span_total_ms=top.total_ms,
            )
        )

    return ProfilingViewModel(
        total_spans=len(spans),
        timeline_points=timeline,
        frame_timeline_points=frame_timeline_points,
        render_timeline_points=render_timeline_points,
        top_total_rows=top_total_rows,
        top_p95_rows=top_p95_rows,
        hitch_correlations=correlations,
    )

from __future__ import annotations

from dataclasses import dataclass

from tools.engine_obs_core.aggregations import detect_hitches, top_span_aggregates
from tools.engine_obs_core.datasource.live_source import LiveSnapshot


@dataclass(frozen=True)
class HitchViewRow:
    tick: int
    frame_ms: float
    top_span: str
    top_span_ms: float


def build_hitch_rows(snapshot: LiveSnapshot, *, threshold_ms: float) -> list[HitchViewRow]:
    points = [
        {
            "tick": point.tick,
            "frame_ms": point.frame_ms,
        }
        for point in snapshot.frame_points
    ]
    hitches = detect_hitches(points, threshold_ms=threshold_ms)
    if not hitches:
        return []
    offenders = top_span_aggregates(snapshot.spans, top_n=1, sort_by="total_ms")
    top_name = offenders[0].key if offenders else ""
    top_ms = offenders[0].total_ms if offenders else 0.0
    return [
        HitchViewRow(
            tick=hitch.tick,
            frame_ms=hitch.frame_ms,
            top_span=top_name,
            top_span_ms=top_ms,
        )
        for hitch in sorted(hitches, key=lambda item: item.frame_ms, reverse=True)
    ]

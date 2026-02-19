from __future__ import annotations

from time import perf_counter

from tools.engine_obs_core.aggregations import compute_frame_stats, top_span_aggregates
from tools.engine_obs_core.contracts import EventRecord, SpanRecord
from tools.engine_obs_core.query import filter_events


def test_core_filter_and_aggregation_performance_budget() -> None:
    events = [
        EventRecord(
            ts_utc=f"2026-01-01T00:00:{idx % 60:02d}.000+00:00",
            tick=idx,
            category="render" if idx % 2 == 0 else "input",
            name="render.frame_ms" if idx % 2 == 0 else "input.pointer_move",
            level="warning" if idx % 97 == 0 else "info",
            value={"value": idx},
            metadata={"idx": idx},
        )
        for idx in range(50_000)
    ]
    spans = [
        SpanRecord(
            tick=idx,
            category="render" if idx % 3 == 0 else "system",
            name="present" if idx % 3 == 0 else "update",
            start_s=0.0,
            end_s=0.0,
            duration_ms=float((idx % 20) + 1),
            metadata={},
        )
        for idx in range(20_000)
    ]
    frame_ms = [float((idx % 25) + 8) for idx in range(50_000)]

    start = perf_counter()
    filtered = filter_events(events, category="render", text="frame")
    stats = compute_frame_stats(frame_ms)
    top = top_span_aggregates(spans, top_n=8, sort_by="total_ms")
    elapsed = perf_counter() - start

    assert len(filtered) > 0
    assert stats.count == 50_000
    assert len(top) > 0
    assert elapsed < 0.75

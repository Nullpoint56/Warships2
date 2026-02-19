from __future__ import annotations

from tools.engine_obs_core.aggregations import top_span_aggregates
from tools.engine_obs_core.contracts import SpanRecord


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


def test_top_span_aggregates_by_total_and_p95() -> None:
    spans = [
        _span(1, "host", "frame", 6.0),
        _span(2, "host", "frame", 7.0),
        _span(3, "module", "on_frame", 3.0),
        _span(4, "module", "on_frame", 4.0),
        _span(5, "render", "present", 8.0),
    ]

    by_total = top_span_aggregates(spans, top_n=2, sort_by="total_ms")
    assert len(by_total) == 2
    assert by_total[0].key == "host:frame"

    by_p95 = top_span_aggregates(spans, top_n=1, sort_by="p95_ms")
    assert len(by_p95) == 1
    assert by_p95[0].key in {"host:frame", "render:present"}


def test_top_span_aggregates_invalid_sort_defaults_to_total() -> None:
    spans = [_span(1, "host", "frame", 5.0), _span(2, "render", "present", 9.0)]
    result = top_span_aggregates(spans, top_n=1, sort_by="not_real")
    assert result[0].key == "render:present"

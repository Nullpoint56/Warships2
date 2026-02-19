from __future__ import annotations

from datetime import datetime

from tools.engine_obs_core.contracts import EventRecord, SpanRecord


def _parse_ts(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def window_events(
    events: list[EventRecord],
    *,
    start_ts_utc: str | None,
    end_ts_utc: str | None,
) -> list[EventRecord]:
    start = _parse_ts(start_ts_utc) if start_ts_utc else None
    end = _parse_ts(end_ts_utc) if end_ts_utc else None
    out: list[EventRecord] = []
    for event in events:
        ts = _parse_ts(event.ts_utc)
        if ts is None:
            continue
        if start is not None and ts < start:
            continue
        if end is not None and ts > end:
            continue
        out.append(event)
    return out


def build_span_bucket_series(
    spans: list[SpanRecord],
    *,
    bucket_size_ticks: int = 10,
) -> list[tuple[int, float]]:
    if not spans:
        return []
    size = max(1, int(bucket_size_ticks))
    buckets: dict[int, list[float]] = {}
    for span in spans:
        bucket = (int(span.tick) // size) * size
        buckets.setdefault(bucket, []).append(float(span.duration_ms))
    points = []
    for bucket_tick in sorted(buckets):
        values = buckets[bucket_tick]
        mean = (sum(values) / len(values)) if values else 0.0
        points.append((bucket_tick, mean))
    return points

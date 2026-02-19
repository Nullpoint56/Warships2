from __future__ import annotations

from dataclasses import dataclass

from tools.engine_obs_core.contracts import SpanRecord


@dataclass(frozen=True)
class FrameStats:
    count: int
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    mean_fps: float


@dataclass(frozen=True)
class HitchRecord:
    tick: int
    frame_ms: float


@dataclass(frozen=True)
class SpanAggregate:
    key: str
    count: int
    total_ms: float
    mean_ms: float
    p95_ms: float
    max_ms: float


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = q * (len(ordered) - 1)
    lo = int(index)
    hi = min(lo + 1, len(ordered) - 1)
    weight = index - lo
    return ordered[lo] * (1.0 - weight) + ordered[hi] * weight


def compute_frame_stats(frame_ms_values: list[float]) -> FrameStats:
    cleaned = [float(v) for v in frame_ms_values if v >= 0.0]
    if not cleaned:
        return FrameStats(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    count = len(cleaned)
    mean_ms = sum(cleaned) / count
    mean_fps = (1000.0 / mean_ms) if mean_ms > 0.0 else 0.0
    return FrameStats(
        count=count,
        mean_ms=mean_ms,
        p50_ms=percentile(cleaned, 0.5),
        p95_ms=percentile(cleaned, 0.95),
        p99_ms=percentile(cleaned, 0.99),
        max_ms=max(cleaned),
        mean_fps=mean_fps,
    )


def detect_hitches(frame_points: list[dict], *, threshold_ms: float) -> list[HitchRecord]:
    hitches: list[HitchRecord] = []
    for point in frame_points:
        tick = int(point.get("tick", 0))
        frame_ms = float(point.get("frame_ms", 0.0))
        if frame_ms >= threshold_ms:
            hitches.append(HitchRecord(tick=tick, frame_ms=frame_ms))
    return hitches


def aggregate_spans(spans: list[SpanRecord]) -> list[SpanAggregate]:
    grouped: dict[str, list[float]] = {}
    for span in spans:
        key = f"{span.category}:{span.name}"
        grouped.setdefault(key, []).append(float(span.duration_ms))

    out: list[SpanAggregate] = []
    for key, durations in grouped.items():
        count = len(durations)
        total = sum(durations)
        mean = total / count if count > 0 else 0.0
        out.append(
            SpanAggregate(
                key=key,
                count=count,
                total_ms=total,
                mean_ms=mean,
                p95_ms=percentile(durations, 0.95),
                max_ms=max(durations) if durations else 0.0,
            )
        )
    return out


def top_span_aggregates(
    spans: list[SpanRecord],
    *,
    top_n: int = 10,
    sort_by: str = "total_ms",
) -> list[SpanAggregate]:
    aggregates = aggregate_spans(spans)
    if sort_by not in {"total_ms", "p95_ms", "mean_ms", "max_ms", "count"}:
        sort_by = "total_ms"
    return sorted(
        aggregates,
        key=lambda agg: getattr(agg, sort_by),
        reverse=True,
    )[: max(1, int(top_n))]

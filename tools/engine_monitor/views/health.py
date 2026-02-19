from __future__ import annotations

from dataclasses import dataclass

from tools.engine_obs_core.aggregations import compute_frame_stats
from tools.engine_obs_core.datasource.live_source import LiveSnapshot


@dataclass(frozen=True)
class HealthViewModel:
    fps: float
    frame_ms_mean: float
    frame_ms_p95: float
    frame_ms_p99: float
    render_ms_mean: float
    max_frame_ms: float
    resize_count: int
    alerts: list[str]


def build_health_view_model(
    snapshot: LiveSnapshot, *, hitch_threshold_ms: float
) -> HealthViewModel:
    frame_values = [
        float(point.frame_ms) for point in snapshot.frame_points if point.frame_ms > 0.0
    ]
    render_values = [
        float(point.render_ms) for point in snapshot.frame_points if point.render_ms > 0.0
    ]
    stats = compute_frame_stats(frame_values)
    render_mean = (sum(render_values) / len(render_values)) if render_values else 0.0
    alerts: list[str] = []
    if stats.p95_ms >= hitch_threshold_ms:
        alerts.append(f"p95 frame time exceeded threshold ({stats.p95_ms:.2f}ms).")
    if snapshot.max_frame_ms >= hitch_threshold_ms * 1.5:
        alerts.append(f"max frame spike detected ({snapshot.max_frame_ms:.2f}ms).")
    return HealthViewModel(
        fps=snapshot.rolling_fps if snapshot.rolling_fps > 0.0 else stats.mean_fps,
        frame_ms_mean=stats.mean_ms,
        frame_ms_p95=stats.p95_ms,
        frame_ms_p99=stats.p99_ms,
        render_ms_mean=render_mean if render_mean > 0.0 else snapshot.rolling_render_ms,
        max_frame_ms=snapshot.max_frame_ms if snapshot.max_frame_ms > 0.0 else stats.max_ms,
        resize_count=snapshot.resize_count,
        alerts=alerts,
    )

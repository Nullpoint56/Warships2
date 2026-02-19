"""View helpers for session summary."""

from __future__ import annotations

from tools.engine_obs_core.aggregations import compute_frame_stats
from tools.engine_obs_core.contracts import CrashBundleRecord, EventRecord
from tools.engine_obs_core.datasource.base import MetricsSnapshot, SessionRef


def build_summary_lines(
    *,
    session: SessionRef | None,
    metrics: MetricsSnapshot,
    events: list[EventRecord],
    crash: CrashBundleRecord | None,
) -> list[str]:
    if session is None:
        return ["No session loaded."]

    frame_values = [point.frame_ms for point in metrics.frame_points]
    stats = compute_frame_stats(frame_values)
    warning_count = sum(1 for event in events if event.level.lower() in {"warn", "warning"})
    error_count = sum(1 for event in events if event.level.lower() in {"error", "critical"})

    run_name = session.run_log.name if session.run_log is not None else "n/a"
    ui_name = session.ui_log.name if session.ui_log is not None else "n/a"

    lines = [
        f"session_id={session.id}",
        f"run_log={run_name}",
        f"ui_log={ui_name}",
        f"events={len(events)}",
        f"frames={len(metrics.frame_points)}",
        f"frame_mean_ms={stats.mean_ms:.3f}",
        f"frame_p95_ms={stats.p95_ms:.3f}",
        f"frame_p99_ms={stats.p99_ms:.3f}",
        f"frame_max_ms={stats.max_ms:.3f}",
        f"fps_mean={stats.mean_fps:.2f}",
        f"warnings={warning_count}",
        f"errors={error_count}",
    ]
    if crash is not None:
        lines.append(f"crash_bundle_tick={crash.tick}")
        lines.append(f"crash_bundle_reason={crash.reason or 'n/a'}")
    else:
        lines.append("crash_bundle_tick=n/a")
        lines.append("crash_bundle_reason=n/a")
    return lines

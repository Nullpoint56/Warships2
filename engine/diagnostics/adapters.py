"""Compatibility adapters from runtime metrics/events into diagnostics events."""

from __future__ import annotations

from typing import Any

from engine.diagnostics.config import load_diagnostics_config
from engine.diagnostics.hub import DiagnosticHub

_DIAGNOSTICS_ADAPTER_CONFIG = load_diagnostics_config()


def emit_frame_metrics(hub: DiagnosticHub, snapshot: Any) -> None:
    """Map runtime metrics snapshot into normalized diagnostics categories."""
    frame = snapshot.last_frame
    if frame is None:
        return
    tick = frame.frame_index
    hub.emit_fast(
        category="frame",
        name="frame.time_ms",
        tick=tick,
        value=frame.dt_ms,
        metadata={"fps_rolling": frame.fps_rolling},
    )
    hub.emit_fast(
        category="scheduler",
        name="scheduler.queue_depth",
        tick=tick,
        value=frame.scheduler_queue_size,
        metadata={
            "enqueued": frame.scheduler_enqueued_count,
            "dequeued": frame.scheduler_dequeued_count,
        },
    )
    hub.emit_fast(
        category="input",
        name="events.publish_count",
        tick=tick,
        value=frame.event_publish_count,
        metadata=(
            {"by_topic": dict(frame.event_publish_by_topic)}
            if _DIAGNOSTICS_ADAPTER_CONFIG.emit_event_topic_breakdown
            else None
        ),
    )
    if _DIAGNOSTICS_ADAPTER_CONFIG.emit_system_timings and frame.system_timings_ms:
        for system_id, elapsed_ms in frame.system_timings_ms.items():
            hub.emit_fast(
                category="system",
                name="system.update_ms",
                tick=tick,
                value=float(elapsed_ms),
                metadata={"system_id": system_id},
            )

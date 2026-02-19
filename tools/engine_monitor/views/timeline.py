from __future__ import annotations

from dataclasses import dataclass

from tools.engine_obs_core.contracts import EventRecord


@dataclass(frozen=True)
class TimelinePoint:
    tick: int
    frame_ms: float
    render_ms: float
    queue_depth: float
    publish_count: float


def build_timeline_points(events: list[EventRecord]) -> list[TimelinePoint]:
    lanes: dict[int, dict[str, float]] = {}
    for event in events:
        tick = int(event.tick)
        bucket = lanes.setdefault(
            tick,
            {
                "frame_ms": 0.0,
                "render_ms": 0.0,
                "queue_depth": 0.0,
                "publish_count": 0.0,
            },
        )
        if event.name == "frame.time_ms" and isinstance(event.value, (int, float)):
            bucket["frame_ms"] = float(event.value)
        elif event.name == "render.frame_ms" and isinstance(event.value, (int, float)):
            bucket["render_ms"] = float(event.value)
        elif event.name == "scheduler.queue_depth" and isinstance(event.value, (int, float)):
            bucket["queue_depth"] = float(event.value)
        elif event.name == "events.publish_count" and isinstance(event.value, (int, float)):
            bucket["publish_count"] = float(event.value)

    return [
        TimelinePoint(
            tick=tick,
            frame_ms=values["frame_ms"],
            render_ms=values["render_ms"],
            queue_depth=values["queue_depth"],
            publish_count=values["publish_count"],
        )
        for tick, values in sorted(lanes.items())
    ]

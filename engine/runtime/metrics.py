"""Runtime metrics collector for lightweight engine diagnostics."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class FrameMetrics:
    """Metrics captured for a single frame."""

    frame_index: int
    dt_ms: float
    fps_rolling: float
    scheduler_queue_size: int
    event_publish_count: int
    scheduler_enqueued_count: int = 0
    scheduler_dequeued_count: int = 0
    event_publish_by_topic: dict[str, int] = field(default_factory=dict)
    system_exception_count: int = 0
    system_timings_ms: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MetricsSnapshot:
    """Read-only snapshot consumable by debug overlay/loggers."""

    last_frame: FrameMetrics | None
    rolling_dt_ms: float
    rolling_fps: float
    top_systems_last_frame: list[tuple[str, float]]


class NoopMetricsCollector:
    """No-op collector for zero-impact disabled mode."""

    def begin_frame(self, frame_index: int) -> None:
        _ = frame_index

    def record_system_time(self, system_name: str, elapsed_ms: float) -> None:
        _ = (system_name, elapsed_ms)

    def set_scheduler_queue_size(self, queue_size: int) -> None:
        _ = queue_size

    def increment_event_publish_count(self, count: int = 1) -> None:
        _ = count

    def increment_event_publish_topic(self, topic: str, count: int = 1) -> None:
        _ = (topic, count)

    def set_scheduler_activity(self, enqueued_count: int, dequeued_count: int) -> None:
        _ = (enqueued_count, dequeued_count)

    def increment_system_exception_count(self, count: int = 1) -> None:
        _ = count

    def end_frame(self, dt_ms: float) -> None:
        _ = dt_ms

    def snapshot(self) -> MetricsSnapshot:
        return MetricsSnapshot(
            last_frame=None,
            rolling_dt_ms=0.0,
            rolling_fps=0.0,
            top_systems_last_frame=[],
        )


class MetricsCollector:
    """Small in-memory rolling metrics collector."""

    def __init__(self, *, window_size: int = 60) -> None:
        self._window_size = max(1, int(window_size))
        self._dt_window: deque[float] = deque(maxlen=self._window_size)
        self._frame_index = 0
        self._scheduler_queue_size = 0
        self._event_publish_count = 0
        self._event_publish_by_topic: dict[str, int] = {}
        self._scheduler_enqueued_count = 0
        self._scheduler_dequeued_count = 0
        self._system_exception_count = 0
        self._system_timings_ms: dict[str, float] = {}
        self._last_frame: FrameMetrics | None = None

    def begin_frame(self, frame_index: int) -> None:
        self._frame_index = frame_index
        self._scheduler_queue_size = 0
        self._event_publish_count = 0
        self._event_publish_by_topic = {}
        self._scheduler_enqueued_count = 0
        self._scheduler_dequeued_count = 0
        self._system_exception_count = 0
        self._system_timings_ms = {}

    def record_system_time(self, system_name: str, elapsed_ms: float) -> None:
        self._system_timings_ms[system_name] = float(elapsed_ms)

    def set_scheduler_queue_size(self, queue_size: int) -> None:
        self._scheduler_queue_size = int(queue_size)

    def increment_event_publish_count(self, count: int = 1) -> None:
        self._event_publish_count += int(count)

    def increment_event_publish_topic(self, topic: str, count: int = 1) -> None:
        normalized = str(topic).strip()
        if not normalized:
            return
        self._event_publish_by_topic[normalized] = (
            self._event_publish_by_topic.get(normalized, 0) + int(count)
        )

    def set_scheduler_activity(self, enqueued_count: int, dequeued_count: int) -> None:
        self._scheduler_enqueued_count = int(enqueued_count)
        self._scheduler_dequeued_count = int(dequeued_count)

    def increment_system_exception_count(self, count: int = 1) -> None:
        self._system_exception_count += int(count)

    def end_frame(self, dt_ms: float) -> FrameMetrics:
        dt = float(dt_ms)
        self._dt_window.append(dt)
        rolling_dt = (sum(self._dt_window) / len(self._dt_window)) if self._dt_window else 0.0
        rolling_fps = (1000.0 / rolling_dt) if rolling_dt > 0.0 else 0.0
        self._last_frame = FrameMetrics(
            frame_index=self._frame_index,
            dt_ms=dt,
            fps_rolling=rolling_fps,
            scheduler_queue_size=self._scheduler_queue_size,
            event_publish_count=self._event_publish_count,
            scheduler_enqueued_count=self._scheduler_enqueued_count,
            scheduler_dequeued_count=self._scheduler_dequeued_count,
            event_publish_by_topic=dict(self._event_publish_by_topic),
            system_exception_count=self._system_exception_count,
            system_timings_ms=dict(self._system_timings_ms),
        )
        return self._last_frame

    def snapshot(self) -> MetricsSnapshot:
        rolling_dt = (sum(self._dt_window) / len(self._dt_window)) if self._dt_window else 0.0
        rolling_fps = (1000.0 / rolling_dt) if rolling_dt > 0.0 else 0.0
        top_systems: list[tuple[str, float]] = []
        if self._last_frame is not None:
            top_systems = sorted(
                self._last_frame.system_timings_ms.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:3]
        return MetricsSnapshot(
            last_frame=self._last_frame,
            rolling_dt_ms=rolling_dt,
            rolling_fps=rolling_fps,
            top_systems_last_frame=top_systems,
        )


def create_metrics_collector(*, enabled: bool, window_size: int = 60) -> MetricsCollector | NoopMetricsCollector:
    """Factory returning enabled collector or no-op implementation."""
    if not enabled:
        return NoopMetricsCollector()
    return MetricsCollector(window_size=window_size)

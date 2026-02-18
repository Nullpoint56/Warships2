"""Rolling aggregate metrics derived from diagnostics events."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from engine.diagnostics.event import DiagnosticEvent


@dataclass(frozen=True, slots=True)
class DiagnosticsMetricsSnapshot:
    frame_count: int
    rolling_frame_ms: float
    rolling_fps: float
    max_frame_ms: float
    resize_count: int
    resize_event_to_apply_p95_ms: float
    resize_apply_to_frame_p95_ms: float
    rolling_render_ms: float


class DiagnosticsMetricsStore:
    """Keep lightweight rolling frame metrics for debug snapshots."""

    def __init__(self, *, window_size: int = 120) -> None:
        self._window_size = max(1, int(window_size))
        self._frame_ms: deque[float] = deque(maxlen=self._window_size)
        self._render_ms: deque[float] = deque(maxlen=self._window_size)
        self._resize_event_to_apply_ms: deque[float] = deque(maxlen=self._window_size)
        self._resize_apply_to_frame_ms: deque[float] = deque(maxlen=self._window_size)
        self._frame_count = 0
        self._max_frame_ms = 0.0
        self._resize_count = 0

    def ingest(self, event: DiagnosticEvent) -> None:
        if event.category == "frame" and event.name == "frame.time_ms":
            if not isinstance(event.value, (int, float)):
                return
            frame_ms = float(event.value)
            self._frame_ms.append(frame_ms)
            self._frame_count += 1
            if frame_ms > self._max_frame_ms:
                self._max_frame_ms = frame_ms
            return
        if event.category == "render" and event.name == "render.frame_ms":
            if isinstance(event.value, (int, float)):
                self._render_ms.append(float(event.value))
            return
        if event.category == "render" and event.name == "render.resize_event":
            self._resize_count += 1
            metadata = event.metadata
            event_to_apply = metadata.get("event_to_apply_ms")
            apply_to_frame = metadata.get("apply_to_frame_ms")
            if isinstance(event_to_apply, (int, float)):
                self._resize_event_to_apply_ms.append(float(event_to_apply))
            if isinstance(apply_to_frame, (int, float)):
                self._resize_apply_to_frame_ms.append(float(apply_to_frame))

    def snapshot(self) -> DiagnosticsMetricsSnapshot:
        if not self._frame_ms:
            return DiagnosticsMetricsSnapshot(
                frame_count=0,
                rolling_frame_ms=0.0,
                rolling_fps=0.0,
                max_frame_ms=0.0,
                resize_count=self._resize_count,
                resize_event_to_apply_p95_ms=0.0,
                resize_apply_to_frame_p95_ms=0.0,
                rolling_render_ms=0.0,
            )
        rolling_frame_ms = sum(self._frame_ms) / len(self._frame_ms)
        rolling_render_ms = (
            (sum(self._render_ms) / len(self._render_ms)) if self._render_ms else 0.0
        )
        rolling_fps = 1000.0 / rolling_frame_ms if rolling_frame_ms > 0.0 else 0.0
        return DiagnosticsMetricsSnapshot(
            frame_count=self._frame_count,
            rolling_frame_ms=rolling_frame_ms,
            rolling_fps=rolling_fps,
            max_frame_ms=self._max_frame_ms,
            resize_count=self._resize_count,
            resize_event_to_apply_p95_ms=_percentile(self._resize_event_to_apply_ms, 0.95),
            resize_apply_to_frame_p95_ms=_percentile(self._resize_apply_to_frame_ms, 0.95),
            rolling_render_ms=rolling_render_ms,
        )


def _percentile(values: deque[float], q: float) -> float:
    if not values:
        return 0.0
    data = sorted(values)
    if len(data) == 1:
        return data[0]
    index = q * (len(data) - 1)
    lo = int(index)
    hi = min(lo + 1, len(data) - 1)
    weight = index - lo
    return data[lo] * (1.0 - weight) + data[hi] * weight

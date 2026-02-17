"""Engine runtime timing primitives."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic


@dataclass(frozen=True, slots=True)
class TimeContext:
    """Per-frame timing context used by runtime and modules."""

    frame_index: int
    delta_seconds: float
    elapsed_seconds: float


class FrameClock:
    """Monotonic frame clock with bounded frame deltas."""

    def __init__(
        self,
        *,
        time_source: Callable[[], float] | None = None,
        max_delta_seconds: float = 0.25,
    ) -> None:
        self._time_source = time_source or monotonic
        self._max_delta_seconds = max_delta_seconds
        self._last_seconds: float | None = None
        self._elapsed_seconds = 0.0

    def next(self, frame_index: int) -> TimeContext:
        """Advance the clock and return the next frame context."""
        now = self._time_source()
        if self._last_seconds is None:
            delta = 0.0
        else:
            raw_delta = now - self._last_seconds
            non_negative_delta = max(0.0, raw_delta)
            delta = min(non_negative_delta, self._max_delta_seconds)
        self._last_seconds = now
        self._elapsed_seconds += delta
        return TimeContext(
            frame_index=frame_index,
            delta_seconds=delta,
            elapsed_seconds=self._elapsed_seconds,
        )


class FixedStepAccumulator:
    """Accumulates variable deltas into fixed-step update counts."""

    def __init__(self, step_seconds: float, *, max_steps_per_frame: int = 8) -> None:
        if step_seconds <= 0.0:
            raise ValueError("step_seconds must be > 0")
        if max_steps_per_frame <= 0:
            raise ValueError("max_steps_per_frame must be > 0")
        self._step_seconds = step_seconds
        self._max_steps_per_frame = max_steps_per_frame
        self._accumulated_seconds = 0.0

    def consume(self, delta_seconds: float) -> int:
        """Return number of fixed steps to execute for this frame."""
        if delta_seconds < 0.0:
            raise ValueError("delta_seconds must be >= 0")
        self._accumulated_seconds += delta_seconds
        steps = int(self._accumulated_seconds // self._step_seconds)
        bounded_steps = min(steps, self._max_steps_per_frame)
        self._accumulated_seconds -= bounded_steps * self._step_seconds
        return bounded_steps

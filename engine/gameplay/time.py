"""Gameplay timing helpers."""

from __future__ import annotations


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


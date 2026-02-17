from __future__ import annotations

import pytest

from engine.runtime.time import FixedStepAccumulator, FrameClock


def test_frame_clock_produces_elapsed_and_delta() -> None:
    values = iter([10.0, 10.1, 10.6])
    clock = FrameClock(time_source=lambda: next(values), max_delta_seconds=0.25)

    frame0 = clock.next(0)
    frame1 = clock.next(1)
    frame2 = clock.next(2)

    assert frame0.delta_seconds == 0.0
    assert frame0.elapsed_seconds == 0.0
    assert frame1.delta_seconds == pytest.approx(0.1)
    assert frame1.elapsed_seconds == pytest.approx(0.1)
    assert frame2.delta_seconds == pytest.approx(0.25)
    assert frame2.elapsed_seconds == pytest.approx(0.35)


def test_frame_clock_clamps_negative_delta() -> None:
    values = iter([5.0, 4.5])
    clock = FrameClock(time_source=lambda: next(values))
    _ = clock.next(0)
    frame1 = clock.next(1)
    assert frame1.delta_seconds == 0.0
    assert frame1.elapsed_seconds == 0.0


def test_fixed_step_accumulator_returns_bounded_steps() -> None:
    accumulator = FixedStepAccumulator(0.1, max_steps_per_frame=2)
    assert accumulator.consume(0.05) == 0
    assert accumulator.consume(0.05) == 1
    assert accumulator.consume(0.3) == 2

from __future__ import annotations

import pytest

from engine.api.context import create_runtime_context
from engine.api.gameplay import SystemSpec, create_update_loop


class _System:
    def __init__(self, system_id: str, events: list[str]) -> None:
        self._id = system_id
        self._events = events

    def start(self, context) -> None:
        _ = context
        self._events.append(f"start:{self._id}")

    def update(self, context, delta_seconds: float) -> None:
        _ = context
        self._events.append(f"update:{self._id}:{delta_seconds:.2f}")

    def shutdown(self, context) -> None:
        _ = context
        self._events.append(f"shutdown:{self._id}")


class _MetricsCollector:
    def __init__(self) -> None:
        self.system_timings: dict[str, float] = {}
        self.system_exceptions = 0

    def record_system_time(self, system_name: str, elapsed_ms: float) -> None:
        self.system_timings[system_name] = elapsed_ms

    def increment_system_exception_count(self, count: int = 1) -> None:
        self.system_exceptions += count


class _FailingSystem(_System):
    def update(self, context, delta_seconds: float) -> None:
        _ = (context, delta_seconds)
        raise RuntimeError("boom")


def test_update_loop_runs_ordered_start_update_shutdown() -> None:
    events: list[str] = []
    loop = create_update_loop()
    loop.add_system(SystemSpec("b", _System("b", events), order=10))
    loop.add_system(SystemSpec("a", _System("a", events), order=0))
    context = create_runtime_context()

    loop.start(context)
    ticks = loop.step(context, 0.16)
    loop.shutdown(context)

    assert ticks == 1
    assert events == [
        "start:a",
        "start:b",
        "update:a:0.16",
        "update:b:0.16",
        "shutdown:b",
        "shutdown:a",
    ]


def test_update_loop_fixed_step_accumulates_ticks() -> None:
    events: list[str] = []
    loop = create_update_loop(fixed_step_seconds=0.1)
    loop.add_system(SystemSpec("a", _System("a", events)))
    context = create_runtime_context()
    loop.start(context)

    ticks = loop.step(context, 0.25)

    assert ticks == 2
    assert events == [
        "start:a",
        "update:a:0.10",
        "update:a:0.10",
    ]


def test_update_loop_validates_inputs_and_duplicates() -> None:
    loop = create_update_loop()
    loop.add_system(SystemSpec("a", _System("a", [])))
    with pytest.raises(ValueError):
        loop.add_system(SystemSpec("a", _System("a2", [])))
    with pytest.raises(ValueError):
        loop.add_system(SystemSpec(" ", _System("x", [])))
    with pytest.raises(ValueError):
        loop.step(create_runtime_context(), -0.1)
    with pytest.raises(ValueError):
        create_update_loop(fixed_step_seconds=0.0)


def test_update_loop_records_system_timings_when_metrics_collector_exists() -> None:
    events: list[str] = []
    metrics = _MetricsCollector()
    loop = create_update_loop()
    loop.add_system(SystemSpec("a", _System("a", events), order=0))
    loop.add_system(SystemSpec("b", _System("b", events), order=1))
    context = create_runtime_context()
    context.provide("metrics_collector", metrics)
    loop.start(context)

    loop.step(context, 0.1)

    assert "a" in metrics.system_timings
    assert "b" in metrics.system_timings
    assert metrics.system_timings["a"] >= 0.0
    assert metrics.system_timings["b"] >= 0.0


def test_update_loop_records_partial_timing_and_exception_count_then_reraises() -> None:
    events: list[str] = []
    metrics = _MetricsCollector()
    loop = create_update_loop()
    loop.add_system(SystemSpec("a", _System("a", events), order=0))
    loop.add_system(SystemSpec("b", _FailingSystem("b", events), order=1))
    context = create_runtime_context()
    context.provide("metrics_collector", metrics)
    loop.start(context)

    with pytest.raises(RuntimeError, match="boom"):
        loop.step(context, 0.1)

    assert "a" in metrics.system_timings
    assert "b" in metrics.system_timings
    assert metrics.system_exceptions == 1

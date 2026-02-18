from __future__ import annotations

import pytest

from engine.api.context import create_runtime_context
from engine.api.gameplay import SystemSpec, create_update_loop


class _MetricsCollector:
    def __init__(self) -> None:
        self.timings: dict[str, float] = {}
        self.exceptions = 0

    def record_system_time(self, system_name: str, elapsed_ms: float) -> None:
        self.timings[system_name] = elapsed_ms

    def increment_system_exception_count(self, count: int = 1) -> None:
        self.exceptions += count


class _System:
    def start(self, context) -> None:
        _ = context

    def update(self, context, delta_seconds: float) -> None:
        _ = (context, delta_seconds)

    def shutdown(self, context) -> None:
        _ = context


class _FailingSystem(_System):
    def update(self, context, delta_seconds: float) -> None:
        _ = (context, delta_seconds)
        raise RuntimeError("system failed")


def test_update_loop_metrics_capture_per_system_timing() -> None:
    metrics = _MetricsCollector()
    context = create_runtime_context()
    context.provide("metrics_collector", metrics)
    loop = create_update_loop()
    loop.add_system(SystemSpec("a", _System(), order=0))
    loop.add_system(SystemSpec("b", _System(), order=1))
    loop.start(context)

    loop.step(context, 0.016)

    assert "a" in metrics.timings
    assert "b" in metrics.timings
    assert metrics.timings["a"] >= 0.0
    assert metrics.timings["b"] >= 0.0


def test_update_loop_metrics_records_exception_count_on_failure() -> None:
    metrics = _MetricsCollector()
    context = create_runtime_context()
    context.provide("metrics_collector", metrics)
    loop = create_update_loop()
    loop.add_system(SystemSpec("ok", _System(), order=0))
    loop.add_system(SystemSpec("fail", _FailingSystem(), order=1))
    loop.start(context)

    with pytest.raises(RuntimeError, match="system failed"):
        loop.step(context, 0.016)

    assert "ok" in metrics.timings
    assert "fail" in metrics.timings
    assert metrics.exceptions == 1

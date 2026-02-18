"""Gameplay update-loop implementation."""

from __future__ import annotations

import logging
from time import perf_counter

from engine.api.context import RuntimeContext
from engine.api.gameplay import SystemSpec
from engine.runtime.time import FixedStepAccumulator

_LOG = logging.getLogger("engine.update")


class RuntimeUpdateLoop:
    """Ordered gameplay update-loop with optional fixed-step mode."""

    def __init__(self, *, fixed_step_seconds: float | None = None) -> None:
        if fixed_step_seconds is not None and fixed_step_seconds <= 0.0:
            raise ValueError("fixed_step_seconds must be > 0")
        self._systems: list[SystemSpec] = []
        self._started_ids: set[str] = set()
        self._cached_order: tuple[SystemSpec, ...] | None = None
        self._accumulator = (
            FixedStepAccumulator(fixed_step_seconds) if fixed_step_seconds is not None else None
        )
        self._fixed_step_seconds = fixed_step_seconds

    def add_system(self, spec: SystemSpec) -> None:
        """Register system spec."""
        normalized_id = spec.system_id.strip()
        if not normalized_id:
            raise ValueError("system_id must not be empty")
        if any(existing.system_id == normalized_id for existing in self._systems):
            raise ValueError(f"duplicate system_id: {normalized_id}")
        self._systems.append(
            SystemSpec(system_id=normalized_id, system=spec.system, order=spec.order)
        )
        self._cached_order = None

    def start(self, context: RuntimeContext) -> None:
        """Start systems in ascending order."""
        for spec in self._ordered_systems():
            if spec.system_id in self._started_ids:
                continue
            spec.system.start(context)
            self._started_ids.add(spec.system_id)

    def step(self, context: RuntimeContext, delta_seconds: float) -> int:
        """Run one frame and return number of ticks executed."""
        if delta_seconds < 0.0:
            raise ValueError("delta_seconds must be >= 0")
        ordered = self._ordered_systems()
        metrics = context.get("metrics_collector")
        system_timings_ms: dict[str, float] = {}
        if self._accumulator is None:
            for spec in ordered:
                if spec.system_id not in self._started_ids:
                    continue
                started_at = perf_counter()
                caught_exc: Exception | None = None
                try:
                    spec.system.update(context, delta_seconds)
                except Exception as exc:
                    caught_exc = exc
                    self._increment_system_exception_count(metrics)
                finally:
                    elapsed_ms = (perf_counter() - started_at) * 1000.0
                    system_timings_ms[spec.system_id] = (
                        system_timings_ms.get(spec.system_id, 0.0) + elapsed_ms
                    )
                if caught_exc is not None:
                    self._publish_system_timings(metrics, system_timings_ms)
                    raise caught_exc
            self._publish_system_timings(metrics, system_timings_ms)
            self._log_system_timings(tick_count=1 if ordered else 0, timings_ms=system_timings_ms)
            return 1 if ordered else 0

        step_seconds = self._fixed_step_seconds
        if step_seconds is None:
            return 0
        tick_count = self._accumulator.consume(delta_seconds)
        for _ in range(tick_count):
            for spec in ordered:
                if spec.system_id not in self._started_ids:
                    continue
                started_at = perf_counter()
                fixed_step_exc: Exception | None = None
                try:
                    spec.system.update(context, step_seconds)
                except Exception as exc:
                    fixed_step_exc = exc
                    self._increment_system_exception_count(metrics)
                finally:
                    elapsed_ms = (perf_counter() - started_at) * 1000.0
                    system_timings_ms[spec.system_id] = (
                        system_timings_ms.get(spec.system_id, 0.0) + elapsed_ms
                    )
                if fixed_step_exc is not None:
                    self._publish_system_timings(metrics, system_timings_ms)
                    raise fixed_step_exc
        self._publish_system_timings(metrics, system_timings_ms)
        self._log_system_timings(tick_count=tick_count, timings_ms=system_timings_ms)
        return tick_count

    def shutdown(self, context: RuntimeContext) -> None:
        """Shutdown started systems in reverse order."""
        for spec in reversed(self._ordered_systems()):
            if spec.system_id not in self._started_ids:
                continue
            spec.system.shutdown(context)
            self._started_ids.remove(spec.system_id)

    def _ordered_systems(self) -> tuple[SystemSpec, ...]:
        if self._cached_order is not None:
            return self._cached_order
        self._cached_order = tuple(
            sorted(
                self._systems,
                key=lambda item: (item.order, item.system_id),
            )
        )
        return self._cached_order

    @staticmethod
    def _publish_system_timings(metrics: object | None, timings_ms: dict[str, float]) -> None:
        if not timings_ms:
            return
        if metrics is None or not hasattr(metrics, "record_system_time"):
            return
        for system_id, elapsed_ms in timings_ms.items():
            metrics.record_system_time(system_id, elapsed_ms)

    @staticmethod
    def _log_system_timings(*, tick_count: int, timings_ms: dict[str, float]) -> None:
        if not timings_ms or not _LOG.isEnabledFor(logging.DEBUG):
            return
        top = sorted(timings_ms.items(), key=lambda item: item[1], reverse=True)[:3]
        top_text = ", ".join(f"{system_id}={elapsed_ms:.3f}ms" for system_id, elapsed_ms in top)
        _LOG.debug("system_timing tick_count=%d systems=%s", tick_count, top_text)

    @staticmethod
    def _increment_system_exception_count(metrics: object | None) -> None:
        if metrics is None or not hasattr(metrics, "increment_system_exception_count"):
            return
        metrics.increment_system_exception_count(1)

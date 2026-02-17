"""Engine runtime deferred and repeating task scheduler."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from heapq import heappop, heappush

TaskCallback = Callable[[], None]


@dataclass(slots=True)
class _Task:
    task_id: int
    due_seconds: float
    callback: TaskCallback
    interval_seconds: float | None = None
    cancelled: bool = False


class Scheduler:
    """Simple time-based scheduler for runtime and modules."""

    def __init__(self) -> None:
        self._now_seconds = 0.0
        self._next_task_id = 1
        self._tasks: dict[int, _Task] = {}
        self._queue: list[tuple[float, int]] = []

    @property
    def now_seconds(self) -> float:
        return self._now_seconds

    @property
    def queued_task_count(self) -> int:
        """Return count of active queued tasks."""
        return sum(1 for task in self._tasks.values() if not task.cancelled)

    def call_later(self, delay_seconds: float, callback: TaskCallback) -> int:
        """Schedule a one-shot callback after delay."""
        if delay_seconds < 0.0:
            raise ValueError("delay_seconds must be >= 0")
        due_seconds = self._now_seconds + delay_seconds
        return self._schedule(due_seconds=due_seconds, callback=callback, interval_seconds=None)

    def call_every(self, interval_seconds: float, callback: TaskCallback) -> int:
        """Schedule a recurring callback at fixed interval."""
        if interval_seconds <= 0.0:
            raise ValueError("interval_seconds must be > 0")
        due_seconds = self._now_seconds + interval_seconds
        return self._schedule(
            due_seconds=due_seconds,
            callback=callback,
            interval_seconds=interval_seconds,
        )

    def cancel(self, task_id: int) -> None:
        """Cancel a scheduled task if it exists."""
        task = self._tasks.get(task_id)
        if task is not None:
            task.cancelled = True

    def advance(self, delta_seconds: float) -> int:
        """Advance scheduler clock and run due callbacks."""
        if delta_seconds < 0.0:
            raise ValueError("delta_seconds must be >= 0")
        self._now_seconds += delta_seconds
        return self.run_due(self._now_seconds)

    def run_due(self, now_seconds: float) -> int:
        """Run callbacks due at or before `now_seconds`."""
        if now_seconds < self._now_seconds:
            raise ValueError("now_seconds cannot move backwards")
        self._now_seconds = now_seconds
        executed = 0
        while self._queue and self._queue[0][0] <= self._now_seconds:
            _, task_id = heappop(self._queue)
            task = self._tasks.get(task_id)
            if task is None or task.cancelled:
                self._tasks.pop(task_id, None)
                continue
            task.callback()
            executed += 1
            if task.cancelled:
                self._tasks.pop(task_id, None)
                continue
            if task.interval_seconds is None:
                self._tasks.pop(task_id, None)
                continue
            task.due_seconds += task.interval_seconds
            heappush(self._queue, (task.due_seconds, task.task_id))
        return executed

    def _schedule(
        self,
        *,
        due_seconds: float,
        callback: TaskCallback,
        interval_seconds: float | None,
    ) -> int:
        task_id = self._next_task_id
        self._next_task_id += 1
        task = _Task(
            task_id=task_id,
            due_seconds=due_seconds,
            callback=callback,
            interval_seconds=interval_seconds,
        )
        self._tasks[task_id] = task
        heappush(self._queue, (due_seconds, task_id))
        return task_id

from __future__ import annotations

import pytest

from engine.runtime.scheduler import Scheduler


def test_scheduler_call_later_runs_when_due() -> None:
    scheduler = Scheduler()
    calls: list[str] = []
    scheduler.call_later(0.2, lambda: calls.append("once"))

    assert scheduler.advance(0.1) == 0
    assert calls == []
    assert scheduler.advance(0.1) == 1
    assert calls == ["once"]


def test_scheduler_call_every_runs_recurring() -> None:
    scheduler = Scheduler()
    calls: list[int] = []
    scheduler.call_every(0.1, lambda: calls.append(1))

    assert scheduler.advance(0.1) == 1
    assert scheduler.advance(0.1) == 1
    assert scheduler.advance(0.1) == 1
    assert len(calls) == 3


def test_scheduler_cancel_prevents_execution() -> None:
    scheduler = Scheduler()
    calls: list[str] = []
    task_id = scheduler.call_later(0.1, lambda: calls.append("never"))
    scheduler.cancel(task_id)
    assert scheduler.advance(0.2) == 0
    assert calls == []


def test_scheduler_validates_time_arguments() -> None:
    scheduler = Scheduler()
    with pytest.raises(ValueError):
        scheduler.call_later(-0.1, lambda: None)
    with pytest.raises(ValueError):
        scheduler.call_every(0.0, lambda: None)
    with pytest.raises(ValueError):
        scheduler.advance(-0.1)


def test_scheduler_queued_task_count_tracks_active_tasks() -> None:
    scheduler = Scheduler()
    one_shot = scheduler.call_later(1.0, lambda: None)
    repeating = scheduler.call_every(1.0, lambda: None)
    assert scheduler.queued_task_count == 2

    scheduler.cancel(one_shot)
    assert scheduler.queued_task_count == 1

    scheduler.advance(1.0)
    assert scheduler.queued_task_count == 1

    scheduler.cancel(repeating)
    assert scheduler.queued_task_count == 0

from __future__ import annotations

from engine.runtime.scheduler import Scheduler


def test_scheduler_reports_queue_size_for_metrics_usage() -> None:
    scheduler = Scheduler()
    scheduler.call_later(1.0, lambda: None)
    scheduler.call_every(1.0, lambda: None)
    assert scheduler.queued_task_count == 2

    scheduler.advance(1.0)
    assert scheduler.queued_task_count == 1


def test_scheduler_reports_enqueued_and_dequeued_activity_counts() -> None:
    scheduler = Scheduler()
    scheduler.call_later(0.0, lambda: None)
    scheduler.call_every(2.0, lambda: None)
    enqueued, dequeued = scheduler.consume_activity_counts()
    assert (enqueued, dequeued) == (2, 0)

    scheduler.advance(0.0)
    enqueued, dequeued = scheduler.consume_activity_counts()
    assert enqueued == 0
    assert dequeued == 1

from __future__ import annotations

from engine.runtime.metrics import MetricsCollector, NoopMetricsCollector, create_metrics_collector


def test_metrics_collector_records_frame_and_top_systems() -> None:
    collector = MetricsCollector(window_size=4)
    collector.begin_frame(1)
    collector.record_system_time("ai", 1.5)
    collector.record_system_time("physics", 4.2)
    collector.record_system_time("ui", 2.0)
    collector.record_system_time("render", 6.1)
    collector.set_scheduler_queue_size(7)
    collector.increment_event_publish_count(3)
    frame = collector.end_frame(16.0)

    assert frame.frame_index == 1
    assert frame.dt_ms == 16.0
    assert frame.scheduler_queue_size == 7
    assert frame.event_publish_count == 3
    assert frame.system_timings_ms["render"] == 6.1

    snap = collector.snapshot()
    assert snap.last_frame is not None
    assert snap.rolling_dt_ms == 16.0
    assert snap.rolling_fps > 0.0
    assert [name for name, _ in snap.top_systems_last_frame] == ["render", "physics", "ui"]


def test_metrics_collector_rolling_window() -> None:
    collector = MetricsCollector(window_size=2)
    collector.begin_frame(1)
    collector.end_frame(10.0)
    collector.begin_frame(2)
    collector.end_frame(30.0)
    collector.begin_frame(3)
    collector.end_frame(50.0)

    snap = collector.snapshot()
    assert snap.rolling_dt_ms == 40.0
    assert snap.rolling_fps == 25.0


def test_noop_collector_is_safe() -> None:
    collector = NoopMetricsCollector()
    collector.begin_frame(1)
    collector.record_system_time("sys", 1.0)
    collector.set_scheduler_queue_size(2)
    collector.increment_event_publish_count()
    collector.end_frame(16.0)
    snap = collector.snapshot()
    assert snap.last_frame is None
    assert snap.rolling_dt_ms == 0.0
    assert snap.rolling_fps == 0.0
    assert snap.top_systems_last_frame == []


def test_factory_returns_expected_type() -> None:
    assert isinstance(create_metrics_collector(enabled=True), MetricsCollector)
    assert isinstance(create_metrics_collector(enabled=False), NoopMetricsCollector)


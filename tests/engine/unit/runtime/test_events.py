from __future__ import annotations

from dataclasses import dataclass

from engine.runtime.events import EventBus


@dataclass(frozen=True, slots=True)
class BaseEvent:
    name: str


@dataclass(frozen=True, slots=True)
class DerivedEvent(BaseEvent):
    code: int


class _MetricsCollector:
    def __init__(self) -> None:
        self.published = 0

    def increment_event_publish_count(self, count: int = 1) -> None:
        self.published += count


def test_event_bus_publish_invokes_subscribers() -> None:
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe(BaseEvent, lambda event: seen.append(event.name))

    invoked = bus.publish(BaseEvent(name="hello"))

    assert invoked == 1
    assert seen == ["hello"]


def test_event_bus_supports_polymorphic_subscription() -> None:
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe(BaseEvent, lambda event: seen.append(event.name))

    invoked = bus.publish(DerivedEvent(name="child", code=42))

    assert invoked == 1
    assert seen == ["child"]


def test_event_bus_unsubscribe_stops_dispatch() -> None:
    bus = EventBus()
    seen: list[str] = []
    subscription = bus.subscribe(BaseEvent, lambda event: seen.append(event.name))
    bus.unsubscribe(subscription)

    invoked = bus.publish(BaseEvent(name="ignored"))

    assert invoked == 0
    assert seen == []


def test_event_bus_increments_publish_metric_when_collector_attached() -> None:
    bus = EventBus()
    metrics = _MetricsCollector()
    bus.set_metrics_collector(metrics)
    bus.subscribe(BaseEvent, lambda event: None)

    bus.publish(BaseEvent(name="hello"))
    bus.publish(BaseEvent(name="again"))

    assert metrics.published == 2

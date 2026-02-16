from __future__ import annotations

from dataclasses import dataclass

from engine.runtime.events import EventBus


@dataclass(frozen=True, slots=True)
class BaseEvent:
    name: str


@dataclass(frozen=True, slots=True)
class DerivedEvent(BaseEvent):
    code: int


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

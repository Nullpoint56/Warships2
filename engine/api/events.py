"""Public event bus API contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, TypeVar

TEvent = TypeVar("TEvent")


@dataclass(frozen=True, slots=True)
class Subscription:
    """Opaque subscription token."""

    id: int


class EventBus(Protocol):
    """Public in-process pub/sub contract."""

    def subscribe(
        self,
        event_type: type[TEvent],
        handler: Callable[[TEvent], None],
    ) -> Subscription:
        """Subscribe handler for event type."""

    def unsubscribe(self, subscription: Subscription) -> None:
        """Unsubscribe token."""

    def publish(self, event: object) -> int:
        """Publish event and return invocation count."""


def create_event_bus() -> EventBus:
    """Create default engine event bus implementation."""
    from engine.runtime.events import RuntimeEventBus

    return RuntimeEventBus()

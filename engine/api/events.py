"""Public event bus API contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable, TypeVar

TEvent = TypeVar("TEvent")


@dataclass(frozen=True, slots=True)
class Subscription:
    """Opaque subscription token."""

    id: int


@runtime_checkable
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

    def publish(self, event: "EventPayload") -> int:
        """Publish event and return invocation count."""


class EventPayload(Protocol):
    """Opaque event payload boundary contract."""

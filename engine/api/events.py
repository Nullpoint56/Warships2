"""Public event bus API contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, TypeVar

TEvent = TypeVar("TEvent")


@dataclass(frozen=True, slots=True)
class Subscription:
    """Opaque subscription token."""

    id: int


class EventBus(ABC):
    """Public in-process pub/sub contract."""

    @abstractmethod
    def subscribe(
        self,
        event_type: type[TEvent],
        handler: Callable[[TEvent], None],
    ) -> Subscription:
        """Subscribe handler for event type."""

    @abstractmethod
    def unsubscribe(self, subscription: Subscription) -> None:
        """Unsubscribe token."""

    @abstractmethod
    def publish(self, event: "EventPayload") -> int:
        """Publish event and return invocation count."""


class EventPayload(Protocol):
    """Opaque event payload boundary contract."""

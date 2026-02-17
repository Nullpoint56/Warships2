"""Lightweight event bus primitives for engine modules."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from engine.api.events import Subscription

TEvent = TypeVar("TEvent")
EventHandler = Callable[[Any], None]


class RuntimeEventBus:
    """Simple in-process pub/sub for engine-local coordination."""

    def __init__(self) -> None:
        self._next_id = 1
        self._subscriptions: dict[int, tuple[type[object], EventHandler]] = {}
        self._metrics_collector: object | None = None

    def set_metrics_collector(self, metrics_collector: object | None) -> None:
        """Attach optional metrics collector used for publish counts."""
        self._metrics_collector = metrics_collector

    def subscribe(
        self,
        event_type: type[TEvent],
        handler: Callable[[TEvent], None],
    ) -> Subscription:
        """Subscribe handler for an event type."""
        sub_id = self._next_id
        self._next_id += 1
        self._subscriptions[sub_id] = (event_type, handler)
        return Subscription(sub_id)

    def unsubscribe(self, subscription: Subscription) -> None:
        """Remove a subscription if present."""
        self._subscriptions.pop(subscription.id, None)

    def publish(self, event: object) -> int:
        """Publish one event and return number of invoked handlers."""
        metrics = self._metrics_collector
        if metrics is not None and hasattr(metrics, "increment_event_publish_count"):
            metrics.increment_event_publish_count(1)
        invoked = 0
        for subscribed_type, handler in tuple(self._subscriptions.values()):
            if isinstance(event, subscribed_type):
                handler(event)
                invoked += 1
        return invoked


EventBus = RuntimeEventBus

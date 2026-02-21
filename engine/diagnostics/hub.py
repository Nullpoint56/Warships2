"""Engine-owned diagnostics hub."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from engine.diagnostics.event import DiagnosticEvent, utc_now_iso
from engine.diagnostics.ring_buffer import RingBuffer

Subscriber = Callable[[DiagnosticEvent], None]


class DiagnosticHub:
    """Central diagnostics event emission and snapshot facility."""

    def __init__(
        self,
        *,
        capacity: int = 10_000,
        enabled: bool = True,
        default_sampling_n: int = 1,
        category_sampling: dict[str, int] | None = None,
        category_allowlist: tuple[str, ...] = (),
    ) -> None:
        self._enabled = bool(enabled)
        self._buffer = RingBuffer[DiagnosticEvent](capacity=capacity)
        self._subscribers: dict[int, Subscriber] = {}
        self._next_subscriber_id = 1
        self._default_sampling_n = max(1, int(default_sampling_n))
        self._category_sampling = {
            str(key).strip().lower(): max(1, int(value))
            for key, value in dict(category_sampling or {}).items()
            if str(key).strip()
        }
        self._category_allowlist = tuple(
            str(item).strip().lower()
            for item in category_allowlist
            if str(item).strip()
        )

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def capacity(self) -> int:
        return self._buffer.capacity

    def emit(self, event: DiagnosticEvent) -> None:
        if not self._enabled:
            return
        self._buffer.append(event)
        for callback in tuple(self._subscribers.values()):
            callback(event)

    def emit_fast(
        self,
        *,
        category: str,
        name: str,
        tick: int,
        level: str = "info",
        value: float | int | str | bool | dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not self._enabled:
            return
        normalized_category = str(category).strip().lower()
        if self._category_allowlist and normalized_category not in self._category_allowlist:
            return
        sampling_n = int(self._category_sampling.get(normalized_category, self._default_sampling_n))
        if sampling_n > 1 and (int(tick) % sampling_n) != 0:
            return
        self.emit(
            DiagnosticEvent(
                ts_utc=utc_now_iso(),
                tick=int(tick),
                category=normalized_category,
                name=name,
                level=level,
                value=value,
                metadata=dict(metadata or {}),
            )
        )

    def subscribe(self, callback: Subscriber) -> int:
        token = self._next_subscriber_id
        self._next_subscriber_id += 1
        self._subscribers[token] = callback
        return token

    def unsubscribe(self, token: int) -> None:
        self._subscribers.pop(token, None)

    def snapshot(
        self,
        *,
        limit: int | None = None,
        category: str | None = None,
        name: str | None = None,
    ) -> list[DiagnosticEvent]:
        events = self._buffer.snapshot(limit=limit)
        if category is not None:
            events = [event for event in events if event.category == category]
        if name is not None:
            events = [event for event in events if event.name == name]
        return events

"""Snapshot exchange primitives for future simulation/render thread split."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class DoubleBufferedSnapshotExchange(Generic[T]):
    """Atomic latest-snapshot exchange with double buffer semantics."""

    _clone_fn: Callable[[T], T] | None = None
    _lock: Lock = field(default_factory=Lock)
    _write_slot: T | None = None
    _read_slot: T | None = None

    def publish(self, snapshot: T | None) -> None:
        """Publish latest snapshot. None clears pending state."""
        with self._lock:
            if snapshot is None:
                self._write_slot = None
                self._read_slot = None
                return
            payload = self._clone_fn(snapshot) if self._clone_fn is not None else snapshot
            self._write_slot = payload

    def consume_latest(self) -> T | None:
        """Consume and clear the latest published snapshot atomically."""
        with self._lock:
            if self._write_slot is None and self._read_slot is None:
                return None
            if self._write_slot is not None:
                self._read_slot = self._write_slot
                self._write_slot = None
            payload = self._read_slot
            self._read_slot = None
            return payload

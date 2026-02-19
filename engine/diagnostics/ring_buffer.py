"""Fixed-capacity ring buffer for diagnostics events."""

from __future__ import annotations


class RingBuffer[T]:
    """Drop-oldest ring buffer with O(1) append."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        self._capacity = int(capacity)
        self._items: list[T | None] = [None] * self._capacity
        self._write_index = 0
        self._size = 0

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def size(self) -> int:
        return self._size

    def append(self, value: T) -> None:
        self._items[self._write_index] = value
        self._write_index = (self._write_index + 1) % self._capacity
        if self._size < self._capacity:
            self._size += 1

    def snapshot(self, *, limit: int | None = None) -> list[T]:
        if self._size == 0:
            return []
        if self._size < self._capacity:
            start = 0
        else:
            start = self._write_index
        out: list[T] = []
        for i in range(self._size):
            idx = (start + i) % self._capacity
            item = self._items[idx]
            if item is not None:
                out.append(item)
        if limit is None or limit >= len(out):
            return out
        return out[-max(0, int(limit)) :]

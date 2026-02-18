from __future__ import annotations

from engine.diagnostics import RingBuffer


def test_ring_buffer_drops_oldest_on_overflow() -> None:
    buffer = RingBuffer[int](capacity=3)
    buffer.append(1)
    buffer.append(2)
    buffer.append(3)
    buffer.append(4)

    assert buffer.snapshot() == [2, 3, 4]


def test_ring_buffer_snapshot_limit_returns_recent_tail() -> None:
    buffer = RingBuffer[int](capacity=5)
    for value in [10, 20, 30, 40]:
        buffer.append(value)

    assert buffer.snapshot(limit=2) == [30, 40]

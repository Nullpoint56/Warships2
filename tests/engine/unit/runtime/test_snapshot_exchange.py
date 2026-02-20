from __future__ import annotations

from engine.runtime.snapshot_exchange import DoubleBufferedSnapshotExchange


def test_snapshot_exchange_consumes_latest_once() -> None:
    exchange = DoubleBufferedSnapshotExchange[int]()
    exchange.publish(1)
    exchange.publish(2)
    assert exchange.consume_latest() == 2
    assert exchange.consume_latest() is None


def test_snapshot_exchange_uses_clone_for_isolation() -> None:
    exchange = DoubleBufferedSnapshotExchange[list[str]](_clone_fn=lambda payload: list(payload))
    source = ["a"]
    exchange.publish(source)
    source.append("b")
    consumed = exchange.consume_latest()
    assert consumed == ["a"]

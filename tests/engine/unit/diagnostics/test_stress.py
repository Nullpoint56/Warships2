from __future__ import annotations

from pathlib import Path

from engine.diagnostics import DiagnosticHub, JsonlAsyncExporter, RingBuffer


def test_ring_buffer_stress_append_and_snapshot_order() -> None:
    capacity = 1024
    total = 50_000
    buffer = RingBuffer[int](capacity=capacity)
    for i in range(total):
        buffer.append(i)
    snapshot = buffer.snapshot()
    assert len(snapshot) == capacity
    assert snapshot[0] == total - capacity
    assert snapshot[-1] == total - 1


def test_async_exporter_backpressure_is_bounded(tmp_path: Path) -> None:
    out = tmp_path / "diag_events.jsonl"
    exporter = JsonlAsyncExporter(path=out, queue_capacity=64)
    hub = DiagnosticHub(enabled=True)
    token = hub.subscribe(exporter.enqueue)
    for i in range(20_000):
        hub.emit_fast(category="frame", name="frame.time_ms", tick=i, value=16.0)
    hub.unsubscribe(token)
    exporter.close(timeout_s=2.0)

    stats = exporter.stats()
    assert stats.written_count >= 1
    assert stats.dropped_count >= 0
    assert stats.queued_count == 0
    assert out.exists()

"""Non-blocking JSONL diagnostics exporter with bounded queue."""

from __future__ import annotations

import json
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.diagnostics.event import DiagnosticEvent


@dataclass(frozen=True, slots=True)
class ExporterStats:
    written_count: int
    dropped_count: int
    queued_count: int


class JsonlAsyncExporter:
    """Background JSONL writer with bounded backpressure queue."""

    def __init__(self, *, path: Path, queue_capacity: int = 2048) -> None:
        self._path = path
        self._queue: queue.Queue[DiagnosticEvent] = queue.Queue(maxsize=max(32, queue_capacity))
        self._stop = threading.Event()
        self._written = 0
        self._dropped = 0
        self._thread = threading.Thread(
            target=self._worker, name="diag-jsonl-exporter", daemon=True
        )
        self._thread.start()

    def enqueue(self, event: DiagnosticEvent) -> None:
        if self._stop.is_set():
            return
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            self._dropped += 1

    def close(self, *, timeout_s: float = 1.0) -> None:
        self._stop.set()
        self._thread.join(timeout=timeout_s)

    def stats(self) -> ExporterStats:
        return ExporterStats(
            written_count=self._written,
            dropped_count=self._dropped,
            queued_count=self._queue.qsize(),
        )

    def _worker(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as out:
            while not self._stop.is_set() or not self._queue.empty():
                try:
                    event = self._queue.get(timeout=0.05)
                except queue.Empty:
                    continue
                payload = _event_to_dict(event)
                out.write(json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
                out.write("\n")
                self._written += 1


def _event_to_dict(event: DiagnosticEvent) -> dict[str, Any]:
    return {
        "ts_utc": event.ts_utc,
        "tick": int(event.tick),
        "category": event.category,
        "name": event.name,
        "level": event.level,
        "value": event.value,
        "metadata": dict(event.metadata),
    }

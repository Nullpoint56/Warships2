"""Diagnostics profiling spans and summaries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from engine.diagnostics.hub import DiagnosticHub
from engine.diagnostics.ring_buffer import RingBuffer
from engine.diagnostics.schema import DIAG_PROFILING_SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class ProfilingSpan:
    tick: int
    category: str
    name: str
    start_s: float
    end_s: float
    duration_ms: float
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ProfilingSnapshot:
    mode: str
    span_count: int
    spans: list[ProfilingSpan]
    top_spans_ms: list[tuple[str, float]]


@dataclass(frozen=True, slots=True)
class _OpenSpan:
    tick: int
    category: str
    name: str
    start_s: float
    metadata: dict[str, Any]


class DiagnosticsProfiler:
    """Collect optional span timings and emit normalized perf diagnostics."""

    def __init__(
        self,
        *,
        mode: str,
        sampling_n: int = 1,
        span_capacity: int = 5_000,
        hub: DiagnosticHub | None = None,
    ) -> None:
        self._mode = mode
        self._sampling_n = max(1, int(sampling_n))
        self._span_buffer = RingBuffer[ProfilingSpan](capacity=max(100, int(span_capacity)))
        self._hub = hub
        self._open: dict[int, _OpenSpan] = {}
        self._next_token = 1
        self._sample_counter = 0

    @property
    def enabled(self) -> bool:
        return self._mode != "off"

    @property
    def timeline_enabled(self) -> bool:
        return self._mode in {"timeline", "timeline_sample"}

    def begin_span(
        self,
        *,
        tick: int,
        category: str,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> int | None:
        if not self.timeline_enabled:
            return None
        token = self._next_token
        self._next_token += 1
        self._open[token] = _OpenSpan(
            tick=int(tick),
            category=str(category),
            name=str(name),
            start_s=perf_counter(),
            metadata=dict(metadata or {}),
        )
        return token

    def end_span(self, token: int | None) -> ProfilingSpan | None:
        if token is None:
            return None
        opened = self._open.pop(token, None)
        if opened is None:
            return None
        end_s = perf_counter()
        span = ProfilingSpan(
            tick=opened.tick,
            category=opened.category,
            name=opened.name,
            start_s=opened.start_s,
            end_s=end_s,
            duration_ms=(end_s - opened.start_s) * 1000.0,
            metadata=opened.metadata,
        )
        self._span_buffer.append(span)
        if self._hub is not None:
            self._hub.emit_fast(
                category="perf",
                name="perf.span",
                tick=span.tick,
                value=span.duration_ms,
                metadata={
                    "span_category": span.category,
                    "span_name": span.name,
                    "start_s": span.start_s,
                    "end_s": span.end_s,
                    **span.metadata,
                },
            )
        return span

    def should_sample(self) -> bool:
        if not self.enabled:
            return False
        self._sample_counter += 1
        return self._sample_counter % self._sampling_n == 0

    def snapshot(self, *, limit: int = 300) -> ProfilingSnapshot:
        spans = self._span_buffer.snapshot(limit=max(1, int(limit)))
        totals: dict[str, float] = {}
        for span in spans:
            key = f"{span.category}:{span.name}"
            totals[key] = totals.get(key, 0.0) + span.duration_ms
        top_spans = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:10]
        return ProfilingSnapshot(
            mode=self._mode,
            span_count=len(spans),
            spans=spans,
            top_spans_ms=top_spans,
        )

    def export_json(self, *, path: Path, limit: int = 3_000) -> Path:
        snapshot = self.snapshot(limit=limit)
        payload = {
            "schema_version": DIAG_PROFILING_SCHEMA_VERSION,
            "mode": snapshot.mode,
            "span_count": snapshot.span_count,
            "top_spans_ms": list(snapshot.top_spans_ms),
            "spans": [
                {
                    "tick": span.tick,
                    "category": span.category,
                    "name": span.name,
                    "start_s": span.start_s,
                    "end_s": span.end_s,
                    "duration_ms": span.duration_ms,
                    "metadata": span.metadata,
                }
                for span in snapshot.spans
            ],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        return path

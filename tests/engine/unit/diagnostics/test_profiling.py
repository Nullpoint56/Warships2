from __future__ import annotations

from pathlib import Path

from engine.diagnostics import DiagnosticHub
from engine.diagnostics.profiling import DiagnosticsProfiler


def test_diagnostics_profiler_collects_spans_and_emits_events() -> None:
    hub = DiagnosticHub(enabled=True)
    profiler = DiagnosticsProfiler(mode="timeline", sampling_n=1, span_capacity=100, hub=hub)

    token = profiler.begin_span(tick=5, category="host", name="frame")
    span = profiler.end_span(token)

    assert span is not None
    snapshot = profiler.snapshot(limit=20)
    assert snapshot.span_count >= 1
    assert snapshot.top_spans_ms
    perf_events = hub.snapshot(category="perf", name="perf.span")
    assert perf_events


def test_diagnostics_profiler_exports_json(tmp_path: Path) -> None:
    profiler = DiagnosticsProfiler(mode="timeline", sampling_n=1, span_capacity=100, hub=None)
    token = profiler.begin_span(tick=1, category="module", name="update")
    profiler.end_span(token)

    out = profiler.export_json(path=tmp_path / "profile.json", limit=50)
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "diag.profiling.v1" in text

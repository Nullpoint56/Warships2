from __future__ import annotations

import argparse
from pathlib import Path
from time import perf_counter

from engine.diagnostics import DiagnosticHub, DiagnosticsProfiler, JsonlAsyncExporter


def _bench_emit(*, enabled: bool, iterations: int) -> float:
    hub = DiagnosticHub(enabled=enabled)
    start = perf_counter()
    for i in range(iterations):
        hub.emit_fast(category="frame", name="frame.time_ms", tick=i, value=16.0)
    elapsed = perf_counter() - start
    return (elapsed * 1000.0) / max(1, iterations)


def _bench_timeline(*, iterations: int) -> float:
    hub = DiagnosticHub(enabled=True)
    profiler = DiagnosticsProfiler(
        mode="timeline", sampling_n=1, span_capacity=iterations + 10, hub=hub
    )
    start = perf_counter()
    for i in range(iterations):
        token = profiler.begin_span(tick=i, category="host", name="frame")
        profiler.end_span(token)
    elapsed = perf_counter() - start
    return (elapsed * 1000.0) / max(1, iterations)


def _bench_exporter_backpressure(
    *, iterations: int, queue_capacity: int, out_file: Path
) -> tuple[int, int]:
    exporter = JsonlAsyncExporter(path=out_file, queue_capacity=queue_capacity)
    hub = DiagnosticHub(enabled=True)
    token = hub.subscribe(exporter.enqueue)
    for i in range(iterations):
        hub.emit_fast(category="frame", name="frame.time_ms", tick=i, value=16.0)
    hub.unsubscribe(token)
    exporter.close(timeout_s=2.0)
    stats = exporter.stats()
    return stats.written_count, stats.dropped_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnostics overhead benchmark.")
    parser.add_argument("--iterations", type=int, default=50_000)
    parser.add_argument("--queue-capacity", type=int, default=512)
    parser.add_argument(
        "--out", type=Path, default=Path("tools/data/profiles/diag_bench_events.jsonl")
    )
    args = parser.parse_args()

    off_ms = _bench_emit(enabled=False, iterations=args.iterations)
    light_ms = _bench_emit(enabled=True, iterations=args.iterations)
    timeline_ms = _bench_timeline(iterations=max(1, args.iterations // 4))
    written, dropped = _bench_exporter_backpressure(
        iterations=args.iterations,
        queue_capacity=args.queue_capacity,
        out_file=args.out,
    )

    print(f"emit_off_ms_per_event={off_ms:.6f}")
    print(f"emit_light_ms_per_event={light_ms:.6f}")
    print(f"timeline_ms_per_span={timeline_ms:.6f}")
    print(f"exporter_written={written}")
    print(f"exporter_dropped={dropped}")
    print(f"exporter_output={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

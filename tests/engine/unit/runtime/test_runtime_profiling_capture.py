from __future__ import annotations

import cProfile

from engine.runtime.metrics import FrameMetrics, MetricsSnapshot
from engine.runtime.profiling import FrameProfiler


def test_frame_profiler_capture_report_includes_latest_render_profile(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_PROFILING_CAPTURE_ENABLED", "0")
    profiler = FrameProfiler(enabled=False, sampling_n=1)
    profiler.set_latest_render_profile(
        {
            "execute_cffi_type_miss_total": 7,
            "execute_cffi_type_miss_delta": 1,
            "execute_cffi_type_miss_unique": 2,
        }
    )

    cpu_prof = cProfile.Profile()
    cpu_prof.enable()
    cpu_prof.disable()

    report = profiler._build_capture_report(frame_index=1, profiler=cpu_prof)  # noqa: SLF001
    render = report.get("render")
    assert isinstance(render, dict)
    latest = render.get("latest_profile")
    assert isinstance(latest, dict)
    assert latest.get("execute_cffi_type_miss_total") == 7
    assert latest.get("execute_cffi_type_miss_delta") == 1
    assert latest.get("execute_cffi_type_miss_unique") == 2


def test_frame_profiler_capture_report_includes_timeline_warmup_summary(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_PROFILING_CAPTURE_ENABLED", "1")
    monkeypatch.setenv("ENGINE_PROFILING_CAPTURE_FRAMES", "999")
    profiler = FrameProfiler(enabled=True, sampling_n=1)
    profiler.on_frame_start(frame_index=0)
    for idx in range(6):
        profiler.set_latest_render_profile({"execute_ms": float(20 - idx)})
        snapshot = MetricsSnapshot(
            last_frame=FrameMetrics(
                frame_index=idx,
                dt_ms=float(20 - idx),
                fps_rolling=float(50 + idx),
                scheduler_queue_size=0,
                event_publish_count=0,
            ),
            rolling_dt_ms=float(20 - idx),
            rolling_fps=float(50 + idx),
            top_systems_last_frame=[],
        )
        _ = profiler.make_profile_payload(snapshot)
        _ = profiler.on_frame_end(frame_index=idx)

    active = profiler._capture_profiler  # noqa: SLF001
    assert isinstance(active, cProfile.Profile)
    active.disable()
    report = profiler._build_capture_report(frame_index=6, profiler=active)  # noqa: SLF001

    timeline = report.get("timeline")
    assert isinstance(timeline, dict)
    samples = timeline.get("samples")
    assert isinstance(samples, list)
    assert len(samples) >= 6
    warmup = timeline.get("warmup_summary")
    assert isinstance(warmup, dict)
    assert warmup.get("sample_count") == len(samples)

"""Structured frame profiling helpers for debug profiling mode."""

from __future__ import annotations

import cProfile
import os
import pstats
import tracemalloc
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from engine.diagnostics.json_codec import dumps_text
from engine.runtime.config import get_runtime_config
from engine.runtime.metrics import MetricsSnapshot

_RSS_PROVIDER: str | None = None
_RSS_PSUTIL_MOD: Any | None = None
_RSS_RESOURCE_MOD: Any | None = None


@dataclass(slots=True)
class FrameProfiler:
    """Collect lightweight profiling payloads at a fixed sampling rate."""

    enabled: bool
    sampling_n: int = 1
    _sampling_n: int = 1
    _sample_counter: int = 0
    _tracemalloc_started: bool = False
    _last_payload: dict[str, Any] | None = None
    _include_system_timings: bool = False
    _include_event_topics: bool = False
    _system_top_n: int = 5
    _capture_enabled: bool = False
    _capture_frames: int = 0
    _capture_top_n: int = 80
    _capture_sort: str = "cumtime"
    _capture_export_dir: Path = Path("tools/data/profiles")
    _capture_start_frame: int | None = None
    _capture_end_frame: int | None = None
    _capture_collected_frames: int = 0
    _capture_report_path: str = ""
    _capture_error: str = ""
    _capture_complete: bool = False
    _capture_profiler: cProfile.Profile | None = None
    _capture_mem_start: tracemalloc.Snapshot | None = None
    _capture_mem_end: tracemalloc.Snapshot | None = None
    _capture_tracemalloc_depth: int = 25
    _capture_report_ready: dict[str, Any] | None = None
    _latest_render_profile: dict[str, Any] | None = None
    _capture_frame_samples: list[dict[str, Any]] = field(default_factory=list)
    _capture_timeline_max: int = 0
    _capture_warmup_frames: int = 0

    def __post_init__(self) -> None:
        profiling_config = get_runtime_config().profiling
        self._sampling_n = max(1, int(self.sampling_n))
        self._include_system_timings = bool(profiling_config.include_system_timings)
        self._include_event_topics = bool(profiling_config.include_event_topics)
        self._system_top_n = max(1, int(profiling_config.system_top_n))
        self._capture_enabled = bool(profiling_config.capture_enabled)
        self._capture_frames = max(1, int(profiling_config.capture_frames))
        self._capture_top_n = max(10, int(profiling_config.capture_top_n))
        self._capture_sort = str(profiling_config.capture_sort).strip().lower()
        self._capture_export_dir = Path(str(profiling_config.capture_export_dir))
        self._capture_tracemalloc_depth = max(1, int(profiling_config.capture_tracemalloc_depth))
        self._capture_timeline_max = max(60, int(profiling_config.capture_timeline_max))
        self._capture_warmup_frames = max(10, int(profiling_config.capture_warmup_frames))
        self._capture_frame_samples = []
        if self.enabled:
            tracemalloc.start(max(1, self._capture_tracemalloc_depth))
            self._tracemalloc_started = True

    def close(self) -> None:
        if self._capture_profiler is not None:
            self._finalize_capture(frame_index=self._capture_end_frame or 0)
        if self._tracemalloc_started:
            tracemalloc.stop()
            self._tracemalloc_started = False

    def on_frame_start(self, *, frame_index: int) -> None:
        if not self._capture_enabled or self._capture_complete:
            return
        if self._capture_profiler is not None:
            return
        if not tracemalloc.is_tracing():
            tracemalloc.start(max(1, self._capture_tracemalloc_depth))
            self._tracemalloc_started = True
        self._capture_start_frame = int(frame_index)
        self._capture_collected_frames = 0
        self._capture_error = ""
        self._capture_frame_samples = []
        self._capture_mem_start = tracemalloc.take_snapshot()
        profile = cProfile.Profile()
        profile.enable()
        self._capture_profiler = profile

    def on_frame_end(self, *, frame_index: int) -> dict[str, Any] | None:
        profiler = self._capture_profiler
        if profiler is None:
            return None
        self._capture_end_frame = int(frame_index)
        self._capture_collected_frames += 1
        if self._capture_collected_frames < self._capture_frames:
            return None
        self._finalize_capture(frame_index=frame_index)
        return self.consume_capture_report_ready()

    def make_profile_payload(self, snapshot: MetricsSnapshot) -> dict[str, Any] | None:
        if not self.enabled or snapshot.last_frame is None:
            return None
        self._capture_timeline_sample(snapshot)
        self._sample_counter += 1
        if self._sample_counter % self._sampling_n != 0:
            return None

        frame = snapshot.last_frame
        top_system_name = ""
        top_system_ms = 0.0
        for system_id, elapsed_ms in frame.system_timings_ms.items():
            ms = float(elapsed_ms)
            if ms > top_system_ms:
                top_system_name = str(system_id)
                top_system_ms = ms
        top_event_name = ""
        top_event_count = 0
        for topic, count in frame.event_publish_by_topic.items():
            topic_count = int(count)
            if topic_count > top_event_count:
                top_event_name = str(topic)
                top_event_count = topic_count
        memory = self._collect_memory()

        bottlenecks: list[str] = []
        if frame.dt_ms >= 25.0:
            bottlenecks.append("frame_hitch")
        if top_system_name:
            bottlenecks.append(f"system:{top_system_name}")
        if top_event_name:
            bottlenecks.append(f"event:{top_event_name}")
        if frame.scheduler_queue_size > 0:
            bottlenecks.append("scheduler_queue")

        events_payload: dict[str, Any] = {
            "publish_count": frame.event_publish_count,
            "top_topic": {"name": top_event_name, "count": int(top_event_count)},
        }
        systems_payload: dict[str, Any] = {
            "top_system": {"name": top_system_name, "ms": float(top_system_ms)},
            "exception_count": frame.system_exception_count,
        }
        top_systems = sorted(
            (
                (str(system_id), float(elapsed_ms))
                for system_id, elapsed_ms in frame.system_timings_ms.items()
            ),
            key=lambda item: item[1],
            reverse=True,
        )[: self._system_top_n]
        systems_payload["top_systems"] = tuple(
            {"name": name, "ms": ms} for name, ms in top_systems
        )
        if self._include_event_topics:
            events_payload["publish_by_topic"] = dict(frame.event_publish_by_topic)
        if self._include_system_timings:
            systems_payload["timings_ms"] = dict(frame.system_timings_ms)
        payload = {
            "schema": "frame_profile_v1",
            "frame_index": frame.frame_index,
            "dt_ms": frame.dt_ms,
            "fps_rolling": frame.fps_rolling,
            "scheduler": {
                "queue_size": frame.scheduler_queue_size,
                "enqueued": frame.scheduler_enqueued_count,
                "dequeued": frame.scheduler_dequeued_count,
            },
            "events": events_payload,
            "systems": systems_payload,
            "memory": memory,
            "render": {
                "latest_profile": dict(self._latest_render_profile or {}),
            },
            "bottlenecks": bottlenecks,
            "capture": self._capture_state_payload(),
        }
        self._last_payload = payload
        return payload

    def set_latest_render_profile(self, profile: dict[str, Any] | None) -> None:
        if isinstance(profile, dict):
            self._latest_render_profile = dict(profile)
        else:
            self._latest_render_profile = None

    @property
    def latest_payload(self) -> dict[str, Any] | None:
        if self._last_payload is None:
            return None
        return dict(self._last_payload)

    def consume_capture_report_ready(self) -> dict[str, Any] | None:
        ready = self._capture_report_ready
        self._capture_report_ready = None
        return ready

    @staticmethod
    def _collect_memory() -> dict[str, float]:
        current_bytes, peak_bytes = tracemalloc.get_traced_memory()
        out: dict[str, float] = {
            "python_current_mb": current_bytes / (1024.0 * 1024.0),
            "python_peak_mb": peak_bytes / (1024.0 * 1024.0),
        }
        rss_mb = _process_rss_mb()
        if rss_mb is not None:
            out["process_rss_mb"] = rss_mb
        return out

    def _capture_state_payload(self) -> dict[str, Any]:
        state = "off"
        if self._capture_enabled:
            state = "complete" if self._capture_complete else "capturing"
        return {
            "state": state,
            "target_frames": int(self._capture_frames),
            "captured_frames": int(self._capture_collected_frames),
            "start_frame": int(self._capture_start_frame) if self._capture_start_frame is not None else -1,
            "end_frame": int(self._capture_end_frame) if self._capture_end_frame is not None else -1,
            "report_path": str(self._capture_report_path),
            "error": str(self._capture_error),
            "top_n": int(self._capture_top_n),
            "sort": str(self._capture_sort),
        }

    def _finalize_capture(self, *, frame_index: int) -> dict[str, Any]:
        profiler = self._capture_profiler
        if profiler is None:
            return self._capture_state_payload()
        profiler.disable()
        self._capture_profiler = None
        report_payload: dict[str, Any] = {}
        try:
            self._capture_mem_end = (
                tracemalloc.take_snapshot() if tracemalloc.is_tracing() else None
            )
            report_payload = self._build_capture_report(frame_index=frame_index, profiler=profiler)
            self._capture_export_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
            out_path = self._capture_export_dir / f"host_profile_capture_{stamp}.json"
            out_path.write_text(dumps_text(report_payload), encoding="utf-8")
            self._capture_report_path = str(out_path)
            self._capture_report_ready = {
                "path": self._capture_report_path,
                "frame_index": int(frame_index),
                "captured_frames": int(self._capture_collected_frames),
            }
        except OSError as exc:
            self._capture_error = f"oserror:{exc}"
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._capture_error = f"capture_failed:{exc}"
        self._capture_complete = True
        return self._capture_state_payload()

    def _build_capture_report(
        self, *, frame_index: int, profiler: cProfile.Profile
    ) -> dict[str, Any]:
        stats_obj = pstats.Stats(profiler)
        stats_map = getattr(stats_obj, "stats", {})
        rows = list(stats_map.items()) if isinstance(stats_map, dict) else []
        if self._capture_sort == "tottime":
            rows.sort(key=lambda item: item[1][2], reverse=True)
        else:
            rows.sort(key=lambda item: item[1][3], reverse=True)
        cpu_top: list[dict[str, Any]] = []
        for (filename, lineno, funcname), stat in rows[: self._capture_top_n]:
            primitive_calls, total_calls, total_time, cumulative_time, _callers = stat
            denom_total = max(1, int(total_calls))
            cpu_top.append(
                {
                    "function": str(funcname),
                    "file": str(filename),
                    "line": int(lineno),
                    "primitive_calls": int(primitive_calls),
                    "total_calls": int(total_calls),
                    "total_time_s": float(total_time),
                    "cumulative_time_s": float(cumulative_time),
                    "avg_total_time_s": float(total_time) / denom_total,
                    "avg_cumulative_time_s": float(cumulative_time) / denom_total,
                }
            )
        memory_top = self._memory_diff_rows()
        return {
            "schema": "host_profile_capture_v1",
            "generated_utc": datetime.now(UTC).isoformat(),
            "frame_index": int(frame_index),
            "capture": {
                "start_frame": int(self._capture_start_frame or 0),
                "end_frame": int(self._capture_end_frame or frame_index),
                "captured_frames": int(self._capture_collected_frames),
                "target_frames": int(self._capture_frames),
                "sort": str(self._capture_sort),
                "top_n": int(self._capture_top_n),
                "report_path": str(self._capture_report_path),
                "error": str(self._capture_error),
            },
            "cpu": {
                "total_calls": int(getattr(stats_obj, "total_calls", 0)),
                "primitive_calls": int(getattr(stats_obj, "prim_calls", 0)),
                "total_time_s": float(getattr(stats_obj, "total_tt", 0.0)),
                "top_functions": cpu_top,
            },
            "memory": {
                "current": self._collect_memory(),
                "top_allocations": memory_top,
            },
            "timeline": {
                "schema": "profile_timeline_v1",
                "samples": list(self._capture_frame_samples),
                "warmup_summary": self._capture_warmup_summary(),
            },
            "render": {
                "latest_profile": dict(self._latest_render_profile or {}),
            },
        }

    def _memory_diff_rows(self) -> list[dict[str, Any]]:
        before = self._capture_mem_start
        after = self._capture_mem_end
        if before is None or after is None:
            return []
        rows: list[dict[str, Any]] = []
        for stat in after.compare_to(before, "lineno")[: self._capture_top_n]:
            frame = stat.traceback[0] if stat.traceback else None
            rows.append(
                {
                    "file": str(frame.filename) if frame is not None else "",
                    "line": int(frame.lineno) if frame is not None else 0,
                    "size_diff_kb": float(stat.size_diff) / 1024.0,
                    "size_kb": float(stat.size) / 1024.0,
                    "count_diff": int(stat.count_diff),
                    "count": int(stat.count),
                }
            )
        return rows

    def _capture_timeline_sample(self, snapshot: MetricsSnapshot) -> None:
        if self._capture_profiler is None:
            return
        frame = snapshot.last_frame
        if frame is None:
            return
        top_system_name = ""
        top_system_ms = 0.0
        for system_id, elapsed_ms in frame.system_timings_ms.items():
            ms = float(elapsed_ms)
            if ms > top_system_ms:
                top_system_name = str(system_id)
                top_system_ms = ms
        render_latest = dict(self._latest_render_profile or {})
        sample = {
            "frame_index": int(frame.frame_index),
            "dt_ms": float(frame.dt_ms),
            "fps_rolling": float(frame.fps_rolling),
            "scheduler_q": int(frame.scheduler_queue_size),
            "events": int(frame.event_publish_count),
            "top_system": {"name": top_system_name, "ms": float(top_system_ms)},
            "render": {
                "total_ms": float(_float_or(render_latest.get("total_ms"), 0.0)),
                "execute_ms": float(_float_or(render_latest.get("execute_ms"), 0.0)),
                "build_ms": float(_float_or(render_latest.get("build_ms"), 0.0)),
                "packet_build_ms": float(
                    _float_or(render_latest.get("execute_packet_build_ms"), 0.0)
                ),
                "backend_draw_ms": float(
                    _float_or(render_latest.get("execute_backend_draw_ms"), 0.0)
                ),
                "translate_ms": float(_float_or(render_latest.get("execute_translate_ms"), 0.0)),
                "expand_ms": float(_float_or(render_latest.get("execute_expand_ms"), 0.0)),
                "draw_packets_total_ms": float(
                    _float_or(render_latest.get("execute_draw_packets_total_ms"), 0.0)
                ),
                "packet_preprocess_ms": float(
                    _float_or(render_latest.get("execute_packet_preprocess_ms"), 0.0)
                ),
                "static_key_build_ms": float(
                    _float_or(render_latest.get("execute_static_key_build_ms"), 0.0)
                ),
                "begin_render_pass_ms": float(
                    _float_or(render_latest.get("execute_begin_render_pass_ms"), 0.0)
                ),
                "render_pass_record_ms": float(
                    _float_or(render_latest.get("execute_render_pass_record_ms"), 0.0)
                ),
                "render_pass_end_ms": float(
                    _float_or(render_latest.get("execute_render_pass_end_ms"), 0.0)
                ),
                "packet_count": int(_int_or(render_latest.get("execute_packet_count"), 0)),
            },
        }
        self._capture_frame_samples.append(sample)
        if len(self._capture_frame_samples) > int(self._capture_timeline_max):
            self._capture_frame_samples = self._capture_frame_samples[-self._capture_timeline_max :]

    def _capture_warmup_summary(self) -> dict[str, Any]:
        samples = self._capture_frame_samples
        if not samples:
            return {}
        n = min(len(samples), int(self._capture_warmup_frames))
        first = samples[:n]
        last = samples[-n:]

        def _mean(rows: list[dict[str, Any]], key_path: tuple[str, ...]) -> float:
            vals: list[float] = []
            for row in rows:
                cur: Any = row
                ok = True
                for key in key_path:
                    if not isinstance(cur, dict) or key not in cur:
                        ok = False
                        break
                    cur = cur[key]
                if not ok:
                    continue
                vals.append(float(_float_or(cur, 0.0)))
            if not vals:
                return 0.0
            return float(sum(vals) / len(vals))

        first_dt = _mean(first, ("dt_ms",))
        last_dt = _mean(last, ("dt_ms",))
        first_fps = _mean(first, ("fps_rolling",))
        last_fps = _mean(last, ("fps_rolling",))
        first_exec = _mean(first, ("render", "execute_ms"))
        last_exec = _mean(last, ("render", "execute_ms"))
        first_packet_build = _mean(first, ("render", "packet_build_ms"))
        last_packet_build = _mean(last, ("render", "packet_build_ms"))
        first_backend_draw = _mean(first, ("render", "backend_draw_ms"))
        last_backend_draw = _mean(last, ("render", "backend_draw_ms"))
        first_render_begin = _mean(first, ("render", "begin_render_pass_ms"))
        last_render_begin = _mean(last, ("render", "begin_render_pass_ms"))
        first_render_record = _mean(first, ("render", "render_pass_record_ms"))
        last_render_record = _mean(last, ("render", "render_pass_record_ms"))
        first_render_end = _mean(first, ("render", "render_pass_end_ms"))
        last_render_end = _mean(last, ("render", "render_pass_end_ms"))
        first_packet_preprocess = _mean(first, ("render", "packet_preprocess_ms"))
        last_packet_preprocess = _mean(last, ("render", "packet_preprocess_ms"))
        first_static_key_build = _mean(first, ("render", "static_key_build_ms"))
        last_static_key_build = _mean(last, ("render", "static_key_build_ms"))
        return {
            "warmup_frames": int(n),
            "sample_count": int(len(samples)),
            "first_mean_dt_ms": float(first_dt),
            "last_mean_dt_ms": float(last_dt),
            "dt_delta_ms": float(first_dt - last_dt),
            "first_mean_fps": float(first_fps),
            "last_mean_fps": float(last_fps),
            "fps_delta": float(last_fps - first_fps),
            "first_render_execute_ms": float(first_exec),
            "last_render_execute_ms": float(last_exec),
            "render_execute_delta_ms": float(first_exec - last_exec),
            "first_packet_build_ms": float(first_packet_build),
            "last_packet_build_ms": float(last_packet_build),
            "packet_build_delta_ms": float(first_packet_build - last_packet_build),
            "first_backend_draw_ms": float(first_backend_draw),
            "last_backend_draw_ms": float(last_backend_draw),
            "backend_draw_delta_ms": float(first_backend_draw - last_backend_draw),
            "first_begin_render_pass_ms": float(first_render_begin),
            "last_begin_render_pass_ms": float(last_render_begin),
            "begin_render_pass_delta_ms": float(first_render_begin - last_render_begin),
            "first_render_pass_record_ms": float(first_render_record),
            "last_render_pass_record_ms": float(last_render_record),
            "render_pass_record_delta_ms": float(first_render_record - last_render_record),
            "first_render_pass_end_ms": float(first_render_end),
            "last_render_pass_end_ms": float(last_render_end),
            "render_pass_end_delta_ms": float(first_render_end - last_render_end),
            "first_packet_preprocess_ms": float(first_packet_preprocess),
            "last_packet_preprocess_ms": float(last_packet_preprocess),
            "packet_preprocess_delta_ms": float(first_packet_preprocess - last_packet_preprocess),
            "first_static_key_build_ms": float(first_static_key_build),
            "last_static_key_build_ms": float(last_static_key_build),
            "static_key_build_delta_ms": float(first_static_key_build - last_static_key_build),
        }


def _process_rss_mb() -> float | None:
    global _RSS_PROVIDER, _RSS_PSUTIL_MOD, _RSS_RESOURCE_MOD

    if _RSS_PROVIDER is None:
        try:
            import psutil  # type: ignore

            _RSS_PSUTIL_MOD = psutil
            _RSS_PROVIDER = "psutil"
        except Exception:
            _RSS_PSUTIL_MOD = None
            if os.name == "nt":
                _RSS_PROVIDER = "win32"
            else:
                try:
                    _RSS_RESOURCE_MOD = import_module("resource")
                    _RSS_PROVIDER = "resource"
                except Exception:
                    _RSS_RESOURCE_MOD = None
                    _RSS_PROVIDER = "none"

    if _RSS_PROVIDER == "psutil" and _RSS_PSUTIL_MOD is not None:
        try:
            process = _RSS_PSUTIL_MOD.Process(os.getpid())
            return float(process.memory_info().rss) / (1024.0 * 1024.0)
        except Exception:
            _RSS_PROVIDER = "win32" if os.name == "nt" else "none"
            _RSS_PSUTIL_MOD = None

    if _RSS_PROVIDER == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            win_dll = getattr(ctypes, "WinDLL", None)
            if not callable(win_dll):
                return None
            kernel32 = win_dll("kernel32", use_last_error=True)
            psapi = win_dll("psapi", use_last_error=True)
            get_current_process = getattr(kernel32, "GetCurrentProcess", None)
            get_process_memory_info = getattr(psapi, "GetProcessMemoryInfo", None)
            if not callable(get_process_memory_info):
                get_process_memory_info = getattr(kernel32, "K32GetProcessMemoryInfo", None)
            if not callable(get_current_process) or not callable(get_process_memory_info):
                return None
            get_process_memory_info.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
                wintypes.DWORD,
            ]
            get_process_memory_info.restype = wintypes.BOOL
            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            process_handle = get_current_process()
            ok = bool(
                get_process_memory_info(
                    process_handle,
                    ctypes.byref(counters),
                    counters.cb,
                )
            )
            if not ok:
                return None
            return float(counters.WorkingSetSize) / (1024.0 * 1024.0)
        except Exception:
            return None

    if _RSS_PROVIDER == "resource" and _RSS_RESOURCE_MOD is not None:
        try:
            resource_mod = _RSS_RESOURCE_MOD
            getrusage = getattr(resource_mod, "getrusage", None)
            rusage_self = getattr(resource_mod, "RUSAGE_SELF", None)
            if not callable(getrusage) or rusage_self is None:
                return None
            usage = getrusage(rusage_self)
            rss_raw = getattr(usage, "ru_maxrss", None)
            if not isinstance(rss_raw, (int, float)):
                return None
            rss = float(rss_raw)
            # Linux reports KB, macOS reports bytes; this heuristic keeps values reasonable.
            if rss > 1024.0 * 1024.0 * 8:
                return rss / (1024.0 * 1024.0)
            return rss / 1024.0
        except Exception:
            return None

    return None


def _float_or(value: object, default: float) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except Exception:
        return float(default)


def _int_or(value: object, default: int) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value))
    except Exception:
        return int(default)

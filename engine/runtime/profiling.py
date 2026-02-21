"""Structured frame profiling helpers for debug profiling mode."""

from __future__ import annotations

import os
import tracemalloc
from importlib import import_module
from dataclasses import dataclass
from typing import Any

from engine.runtime.metrics import MetricsSnapshot


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

    def __post_init__(self) -> None:
        self._sampling_n = max(1, int(self.sampling_n))
        self._include_system_timings = _env_flag("ENGINE_PROFILING_INCLUDE_SYSTEM_TIMINGS", False)
        self._include_event_topics = _env_flag("ENGINE_PROFILING_INCLUDE_EVENT_TOPICS", False)
        if self.enabled:
            tracemalloc.start()
            self._tracemalloc_started = True

    def close(self) -> None:
        if self._tracemalloc_started:
            tracemalloc.stop()
            self._tracemalloc_started = False

    def make_profile_payload(self, snapshot: MetricsSnapshot) -> dict[str, Any] | None:
        if not self.enabled or snapshot.last_frame is None:
            return None
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
            "bottlenecks": bottlenecks,
        }
        self._last_payload = payload
        return payload

    @property
    def latest_payload(self) -> dict[str, Any] | None:
        if self._last_payload is None:
            return None
        return dict(self._last_payload)

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


def _process_rss_mb() -> float | None:
    try:
        import psutil  # type: ignore

        process = psutil.Process(os.getpid())
        return float(process.memory_info().rss) / (1024.0 * 1024.0)
    except Exception:
        pass

    if os.name == "nt":
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

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
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
            pass

    try:
        resource_mod = import_module("resource")
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


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return bool(default)
    value = str(raw).strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return bool(default)

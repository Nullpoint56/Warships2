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

    def __post_init__(self) -> None:
        self._sampling_n = max(1, int(self.sampling_n))
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
        systems = dict(frame.system_timings_ms)
        top_system = max(systems.items(), key=lambda item: item[1], default=("", 0.0))
        events = dict(frame.event_publish_by_topic)
        top_event = max(events.items(), key=lambda item: item[1], default=("", 0))
        memory = self._collect_memory()

        bottlenecks: list[str] = []
        if frame.dt_ms >= 25.0:
            bottlenecks.append("frame_hitch")
        if top_system[0]:
            bottlenecks.append(f"system:{top_system[0]}")
        if top_event[0]:
            bottlenecks.append(f"event:{top_event[0]}")
        if frame.scheduler_queue_size > 0:
            bottlenecks.append("scheduler_queue")

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
            "events": {
                "publish_count": frame.event_publish_count,
                "publish_by_topic": events,
                "top_topic": {"name": top_event[0], "count": int(top_event[1])},
            },
            "systems": {
                "timings_ms": systems,
                "top_system": {"name": top_system[0], "ms": float(top_system[1])},
                "exception_count": frame.system_exception_count,
            },
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

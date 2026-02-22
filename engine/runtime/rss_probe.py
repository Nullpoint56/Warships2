"""Process RSS probing helpers for profiling."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from importlib import import_module
from typing import Any

_LOG = logging.getLogger("engine.profiling")


@dataclass(slots=True)
class ProcessRssProbe:
    provider: str | None = None
    psutil_mod: Any | None = None
    resource_mod: Any | None = None

    def read_mb(self) -> float | None:
        if self.provider is None:
            try:
                import psutil  # type: ignore

                self.psutil_mod = psutil
                self.provider = "psutil"
            except (RuntimeError, OSError, ValueError, TypeError, AttributeError, ImportError):
                self.psutil_mod = None
                _LOG.debug("profiling_rss_psutil_unavailable", exc_info=True)
                if os.name == "nt":
                    self.provider = "win32"
                else:
                    try:
                        self.resource_mod = import_module("resource")
                        self.provider = "resource"
                    except (RuntimeError, OSError, ValueError, TypeError, AttributeError, ImportError):
                        self.resource_mod = None
                        _LOG.debug("profiling_rss_resource_unavailable", exc_info=True)
                        self.provider = "none"

        if self.provider == "psutil" and self.psutil_mod is not None:
            try:
                process = self.psutil_mod.Process(os.getpid())
                return float(process.memory_info().rss) / (1024.0 * 1024.0)
            except (RuntimeError, OSError, ValueError, TypeError, AttributeError, ImportError):
                self.provider = "win32" if os.name == "nt" else "none"
                self.psutil_mod = None
                _LOG.debug("profiling_rss_psutil_probe_failed", exc_info=True)

        if self.provider == "win32":
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
            except (RuntimeError, OSError, ValueError, TypeError, AttributeError, ImportError):
                _LOG.debug("profiling_rss_win32_probe_failed", exc_info=True)
                return None

        if self.provider == "resource" and self.resource_mod is not None:
            try:
                resource_mod = self.resource_mod
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
            except (RuntimeError, OSError, ValueError, TypeError, AttributeError, ImportError):
                _LOG.debug("profiling_rss_resource_probe_failed", exc_info=True)
                return None

        return None


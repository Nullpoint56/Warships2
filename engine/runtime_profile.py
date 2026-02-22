"""Runtime profile presets for performance/debug behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

type RuntimeProfileName = Literal["dev-debug", "dev-fast", "release-like"]


@dataclass(frozen=True, slots=True)
class RuntimeProfile:
    """Resolved runtime profile defaults."""

    name: RuntimeProfileName
    log_level: str
    metrics_enabled: bool
    overlay_enabled: bool
    profiling_enabled: bool
    profiling_sampling_n: int
    render_loop_mode: str
    render_fps_cap: float
    render_vsync: bool
    diagnostics_enabled: bool
    diagnostics_buffer_cap: int
    diagnostics_profile_mode: str
    diagnostics_profile_sampling_n: int
    diagnostics_default_sampling_n: int
    diagnostics_category_allowlist_csv: str
    diagnostics_category_sampling_csv: str


_PROFILE_PRESETS: dict[RuntimeProfileName, RuntimeProfile] = {
    "dev-debug": RuntimeProfile(
        name="dev-debug",
        log_level="DEBUG",
        metrics_enabled=True,
        overlay_enabled=True,
        profiling_enabled=True,
        profiling_sampling_n=1,
        render_loop_mode="continuous",
        render_fps_cap=0.0,
        render_vsync=False,
        diagnostics_enabled=True,
        diagnostics_buffer_cap=20_000,
        diagnostics_profile_mode="timeline",
        diagnostics_profile_sampling_n=1,
        diagnostics_default_sampling_n=1,
        diagnostics_category_allowlist_csv="",
        diagnostics_category_sampling_csv="",
    ),
    "dev-fast": RuntimeProfile(
        name="dev-fast",
        log_level="INFO",
        metrics_enabled=False,
        overlay_enabled=False,
        profiling_enabled=False,
        profiling_sampling_n=8,
        render_loop_mode="continuous",
        render_fps_cap=0.0,
        render_vsync=False,
        diagnostics_enabled=True,
        diagnostics_buffer_cap=8_000,
        diagnostics_profile_mode="light",
        diagnostics_profile_sampling_n=8,
        diagnostics_default_sampling_n=4,
        diagnostics_category_allowlist_csv="frame,render,window,perf,error",
        diagnostics_category_sampling_csv="render:2,frame:2,window:1,error:1",
    ),
    "release-like": RuntimeProfile(
        name="release-like",
        log_level="INFO",
        metrics_enabled=False,
        overlay_enabled=False,
        profiling_enabled=False,
        profiling_sampling_n=16,
        render_loop_mode="on_demand",
        render_fps_cap=60.0,
        render_vsync=True,
        diagnostics_enabled=True,
        diagnostics_buffer_cap=4_000,
        diagnostics_profile_mode="off",
        diagnostics_profile_sampling_n=16,
        diagnostics_default_sampling_n=1,
        diagnostics_category_allowlist_csv="",
        diagnostics_category_sampling_csv="",
    ),
}


def normalize_runtime_profile_name(
    raw: str | None, default: RuntimeProfileName = "release-like"
) -> RuntimeProfileName:
    """Normalize runtime profile name from a raw string."""
    if raw is None:
        return default
    normalized = str(raw).strip().lower()
    alias_map: dict[str, RuntimeProfileName] = {
        "dev-debug": "dev-debug",
        "dev_debug": "dev-debug",
        "debug": "dev-debug",
        "dev-fast": "dev-fast",
        "dev_fast": "dev-fast",
        "fast": "dev-fast",
        "release-like": "release-like",
        "release_like": "release-like",
        "release": "release-like",
        "prod": "release-like",
    }
    return alias_map.get(normalized, default)


def resolve_runtime_profile_name(default: RuntimeProfileName = "release-like") -> RuntimeProfileName:
    """Resolve runtime profile name without environment lookup."""
    return default


def resolve_runtime_profile(
    default: RuntimeProfileName = "release-like",
    *,
    profile_name: RuntimeProfileName | None = None,
) -> RuntimeProfile:
    """Return full runtime profile defaults."""
    name = profile_name or default
    return _PROFILE_PRESETS[name]


__all__ = [
    "RuntimeProfile",
    "RuntimeProfileName",
    "normalize_runtime_profile_name",
    "resolve_runtime_profile",
    "resolve_runtime_profile_name",
]

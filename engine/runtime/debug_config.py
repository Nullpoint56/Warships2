"""Engine-wide debug configuration sourced from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass

from engine.runtime_profile import resolve_runtime_profile


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True, slots=True)
class DebugConfig:
    """Immutable runtime debug configuration."""

    metrics_enabled: bool
    overlay_enabled: bool
    log_level: str
    profiling_enabled: bool = False
    profiling_sampling_n: int = 1


def resolve_log_level_name(default: str = "INFO") -> str:
    """Resolve runtime log level with engine-prefixed override."""
    value = os.getenv("ENGINE_LOG_LEVEL")
    if value is None:
        value = os.getenv("LOG_LEVEL", default)
    return value.strip().upper()


def load_debug_config() -> DebugConfig:
    """Load immutable debug configuration from env vars."""
    profile = resolve_runtime_profile()
    return DebugConfig(
        metrics_enabled=_flag("ENGINE_METRICS_ENABLED", profile.metrics_enabled),
        overlay_enabled=_flag("ENGINE_UI_OVERLAY_ENABLED", profile.overlay_enabled),
        profiling_enabled=_flag("ENGINE_PROFILING_ENABLED", profile.profiling_enabled),
        profiling_sampling_n=max(1, _int("ENGINE_PROFILING_SAMPLING_N", profile.profiling_sampling_n)),
        log_level=resolve_log_level_name(default=profile.log_level),
    )


def enabled_metrics() -> bool:
    return load_debug_config().metrics_enabled


def enabled_overlay() -> bool:
    return load_debug_config().overlay_enabled


def enabled_profiling() -> bool:
    return load_debug_config().profiling_enabled

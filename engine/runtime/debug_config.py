"""Engine-wide debug configuration sourced from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


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


def _csv(name: str) -> tuple[str, ...]:
    raw = os.getenv(name)
    if raw is None:
        return ()
    values = [part.strip() for part in raw.split(",")]
    return tuple(value for value in values if value)


@dataclass(frozen=True, slots=True)
class DebugConfig:
    """Immutable runtime debug configuration."""

    metrics_enabled: bool
    overlay_enabled: bool
    ui_trace_enabled: bool
    resize_trace_enabled: bool
    ui_trace_sampling_n: int
    ui_trace_auto_dump: bool
    ui_trace_dump_dir: str
    log_level: str
    ui_trace_primitives_enabled: bool = True
    ui_trace_key_filter: tuple[str, ...] = field(default_factory=tuple)
    ui_trace_log_every_frame: bool = False


def resolve_log_level_name(default: str = "INFO") -> str:
    """Resolve runtime log level with engine-prefixed override."""
    value = os.getenv("ENGINE_LOG_LEVEL")
    if value is None:
        value = os.getenv("LOG_LEVEL", default)
    return value.strip().upper()


def load_debug_config() -> DebugConfig:
    """Load immutable debug configuration from env vars."""
    return DebugConfig(
        metrics_enabled=_flag("ENGINE_DEBUG_METRICS", False),
        overlay_enabled=_flag("ENGINE_DEBUG_OVERLAY", False),
        ui_trace_enabled=_flag("ENGINE_DEBUG_UI_TRACE", False),
        resize_trace_enabled=_flag("ENGINE_DEBUG_RESIZE_TRACE", False),
        ui_trace_sampling_n=max(1, _int("ENGINE_DEBUG_UI_TRACE_SAMPLING_N", 10)),
        ui_trace_auto_dump=_flag("ENGINE_DEBUG_UI_TRACE_AUTO_DUMP", False),
        ui_trace_dump_dir=os.getenv("ENGINE_DEBUG_UI_TRACE_DUMP_DIR", "logs").strip() or "logs",
        ui_trace_primitives_enabled=_flag("ENGINE_DEBUG_UI_TRACE_PRIMITIVES", True),
        ui_trace_key_filter=_csv("ENGINE_DEBUG_UI_TRACE_KEY_FILTER"),
        ui_trace_log_every_frame=_flag("ENGINE_DEBUG_UI_TRACE_LOG_EVERY_FRAME", False),
        log_level=resolve_log_level_name(),
    )


def enabled_metrics() -> bool:
    return load_debug_config().metrics_enabled


def enabled_overlay() -> bool:
    return load_debug_config().overlay_enabled


def enabled_ui_trace() -> bool:
    return load_debug_config().ui_trace_enabled


def enabled_resize_trace() -> bool:
    return load_debug_config().resize_trace_enabled

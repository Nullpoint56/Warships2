"""Diagnostics capability configuration from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _flag(name: str, default: bool) -> bool:
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


def _str(name: str, default: str) -> str:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip()
    return value if value else default


@dataclass(frozen=True, slots=True)
class DiagnosticsConfig:
    enabled: bool = True
    buffer_capacity: int = 10_000
    crash_bundle_enabled: bool = True
    crash_bundle_dir: str = "appdata/crash"
    crash_recent_events_limit: int = 400
    profile_mode: str = "off"
    profile_sampling_n: int = 1
    profile_span_capacity: int = 5_000
    profile_export_dir: str = "appdata/profiling"
    replay_capture: bool = False
    replay_export_dir: str = "appdata/replay"
    replay_hash_interval: int = 60


def load_diagnostics_config() -> DiagnosticsConfig:
    mode = _str("ENGINE_DIAG_PROFILE_MODE", "off").lower()
    if mode not in {"off", "light", "timeline", "timeline_sample"}:
        mode = "off"
    return DiagnosticsConfig(
        enabled=_flag("ENGINE_DIAG_ENABLED", True),
        buffer_capacity=max(100, _int("ENGINE_DIAG_BUFFER_CAP", 10_000)),
        crash_bundle_enabled=_flag("ENGINE_DIAG_CRASH_BUNDLE", True),
        crash_bundle_dir=_str("ENGINE_DIAG_CRASH_DIR", "appdata/crash"),
        crash_recent_events_limit=max(10, _int("ENGINE_DIAG_CRASH_RECENT_EVENTS", 400)),
        profile_mode=mode,
        profile_sampling_n=max(1, _int("ENGINE_DIAG_PROFILE_SAMPLING_N", 1)),
        profile_span_capacity=max(100, _int("ENGINE_DIAG_PROFILE_SPAN_CAP", 5_000)),
        profile_export_dir=_str("ENGINE_DIAG_PROFILE_EXPORT_DIR", "appdata/profiling"),
        replay_capture=_flag("ENGINE_DIAG_REPLAY_CAPTURE", False),
        replay_export_dir=_str("ENGINE_DIAG_REPLAY_EXPORT_DIR", "appdata/replay"),
        replay_hash_interval=max(1, _int("ENGINE_DIAG_REPLAY_HASH_INTERVAL", 60)),
    )


def resolve_crash_bundle_dir(config: DiagnosticsConfig) -> Path:
    return Path(config.crash_bundle_dir)

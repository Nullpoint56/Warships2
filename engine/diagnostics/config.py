"""Diagnostics capability configuration from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from engine.runtime_profile import resolve_runtime_profile

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
    event_default_sampling_n: int = 1
    event_category_sampling: dict[str, int] = field(default_factory=dict)
    event_category_allowlist: tuple[str, ...] = ()


def load_diagnostics_config() -> DiagnosticsConfig:
    profile = resolve_runtime_profile()
    mode = _str("ENGINE_DIAGNOSTICS_PROFILING_MODE", profile.diagnostics_profile_mode).lower()
    if mode not in {"off", "light", "timeline", "timeline_sample"}:
        mode = profile.diagnostics_profile_mode
    category_sampling = _parse_category_sampling(
        _str("ENGINE_DIAGNOSTICS_CATEGORY_SAMPLING", profile.diagnostics_category_sampling_csv)
    )
    category_allowlist = _parse_category_allowlist(
        _str("ENGINE_DIAGNOSTICS_CATEGORY_ALLOWLIST", profile.diagnostics_category_allowlist_csv)
    )
    return DiagnosticsConfig(
        enabled=_flag("ENGINE_DIAGNOSTICS_ENABLED", profile.diagnostics_enabled),
        buffer_capacity=max(100, _int("ENGINE_DIAGNOSTICS_BUFFER_CAP", profile.diagnostics_buffer_cap)),
        crash_bundle_enabled=_flag("ENGINE_DIAGNOSTICS_CRASH_ENABLED", True),
        crash_bundle_dir=_str("ENGINE_DIAGNOSTICS_CRASH_DIR", "appdata/crash"),
        crash_recent_events_limit=max(10, _int("ENGINE_DIAGNOSTICS_CRASH_RECENT_EVENTS", 400)),
        profile_mode=mode,
        profile_sampling_n=max(1, _int("ENGINE_DIAGNOSTICS_PROFILING_SAMPLING_N", profile.diagnostics_profile_sampling_n)),
        profile_span_capacity=max(100, _int("ENGINE_DIAGNOSTICS_PROFILING_SPAN_CAP", 5_000)),
        profile_export_dir=_str("ENGINE_DIAGNOSTICS_PROFILING_EXPORT_DIR", "appdata/profiling"),
        replay_capture=_flag("ENGINE_DIAGNOSTICS_REPLAY_ENABLED", False),
        replay_export_dir=_str("ENGINE_DIAGNOSTICS_REPLAY_EXPORT_DIR", "appdata/replay"),
        replay_hash_interval=max(1, _int("ENGINE_DIAGNOSTICS_REPLAY_HASH_INTERVAL", 60)),
        event_default_sampling_n=max(1, _int("ENGINE_DIAGNOSTICS_DEFAULT_SAMPLING_N", profile.diagnostics_default_sampling_n)),
        event_category_sampling=category_sampling,
        event_category_allowlist=category_allowlist,
    )


def resolve_crash_bundle_dir(config: DiagnosticsConfig) -> Path:
    return Path(config.crash_bundle_dir)


def _parse_category_sampling(raw: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for part in raw.split(","):
        chunk = part.strip().lower()
        if not chunk or ":" not in chunk:
            continue
        category, sampling = chunk.split(":", 1)
        category_name = category.strip()
        if not category_name:
            continue
        try:
            n = int(sampling.strip())
        except ValueError:
            continue
        out[category_name] = max(1, n)
    return out


def _parse_category_allowlist(raw: str) -> tuple[str, ...]:
    values = tuple(item.strip().lower() for item in raw.split(",") if item.strip())
    return tuple(dict.fromkeys(values))

"""Unified Warships app-data paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def resolve_app_data_root() -> Path:
    """Resolve app-data root directory for Warships runtime state."""
    configured = os.getenv("WARSHIPS_APP_DATA_DIR", "").strip()
    if configured:
        candidate = Path(configured)
        if candidate.is_absolute():
            return candidate
        return resolve_game_root() / candidate
    return resolve_game_root() / "appdata"


def resolve_game_root() -> Path:
    """Resolve the runtime game root directory."""
    if getattr(sys, "frozen", False):
        executable = getattr(sys, "executable", "")
        if executable:
            return Path(executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def resolve_logs_dir() -> Path:
    """Resolve logs directory under app-data root."""
    return resolve_app_data_root() / "logs"


def resolve_ui_dir() -> Path:
    """Resolve UI data directory under app-data root."""
    return resolve_app_data_root() / "ui"


def resolve_profiling_dir() -> Path:
    """Resolve profiling directory under app-data root."""
    return resolve_app_data_root() / "profiling"


def resolve_replay_dir() -> Path:
    """Resolve replay directory under app-data root."""
    return resolve_app_data_root() / "replay"


def resolve_crash_dir() -> Path:
    """Resolve crash bundle directory under app-data root."""
    return resolve_app_data_root() / "crash"


def resolve_presets_dir() -> Path:
    """Resolve presets directory under app-data root."""
    return resolve_app_data_root() / "presets"


def resolve_saves_dir() -> Path:
    """Resolve saves directory under app-data root."""
    return resolve_app_data_root() / "saves"


def ensure_app_data_dirs() -> dict[str, Path]:
    """Create app-data directories and return resolved paths."""
    root = resolve_app_data_root()
    logs = resolve_logs_dir()
    ui = resolve_ui_dir()
    profiling = resolve_profiling_dir()
    replay = resolve_replay_dir()
    crash = resolve_crash_dir()
    presets = resolve_presets_dir()
    saves = resolve_saves_dir()
    root.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    ui.mkdir(parents=True, exist_ok=True)
    profiling.mkdir(parents=True, exist_ok=True)
    replay.mkdir(parents=True, exist_ok=True)
    crash.mkdir(parents=True, exist_ok=True)
    presets.mkdir(parents=True, exist_ok=True)
    saves.mkdir(parents=True, exist_ok=True)
    return {
        "root": root,
        "logs": logs,
        "ui": ui,
        "profiling": profiling,
        "replay": replay,
        "crash": crash,
        "presets": presets,
        "saves": saves,
    }


def apply_runtime_path_defaults() -> dict[str, Path]:
    """Set default runtime path env vars to unified app-data locations."""
    paths = ensure_app_data_dirs()
    log_dir = _normalize_runtime_path_env("WARSHIPS_LOG_DIR", paths["logs"])
    presets_dir = _normalize_runtime_path_env("WARSHIPS_PRESETS_DIR", paths["presets"])
    profiling_dir = _normalize_runtime_path_env(
        "ENGINE_DIAGNOSTICS_PROFILING_EXPORT_DIR", paths["profiling"]
    )
    replay_dir = _normalize_runtime_path_env("ENGINE_DIAGNOSTICS_REPLAY_EXPORT_DIR", paths["replay"])
    crash_dir = _normalize_runtime_path_env("ENGINE_DIAGNOSTICS_CRASH_DIR", paths["crash"])

    log_dir.mkdir(parents=True, exist_ok=True)
    presets_dir.mkdir(parents=True, exist_ok=True)
    paths["ui"].mkdir(parents=True, exist_ok=True)
    profiling_dir.mkdir(parents=True, exist_ok=True)
    replay_dir.mkdir(parents=True, exist_ok=True)
    crash_dir.mkdir(parents=True, exist_ok=True)

    return {
        "root": paths["root"],
        "logs": log_dir,
        "ui": paths["ui"],
        "profiling": profiling_dir,
        "replay": replay_dir,
        "crash": crash_dir,
        "presets": presets_dir,
        "saves": paths["saves"],
    }


def _normalize_runtime_path_env(var_name: str, default_path: Path) -> Path:
    raw = os.getenv(var_name, "").strip()
    if not raw:
        os.environ[var_name] = str(default_path)
        return default_path
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    normalized = resolve_app_data_root() / candidate
    os.environ[var_name] = str(normalized)
    return normalized

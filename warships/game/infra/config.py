"""Application configuration and env loading."""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from pathlib import Path


def load_env_file(path: str = ".env", *, override_existing: bool = True) -> None:
    """Load KEY=VALUE pairs from an env file into process environment.

    By default, values from the env file overwrite existing environment variables.
    """
    env_path = _resolve_env_path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        if override_existing or key not in os.environ:
            os.environ[key] = value


def load_default_env_files(
    *, override_existing: bool = True, paths: Sequence[str] | None = None
) -> None:
    """Load split env files with optional local overrides.

    Precedence is left-to-right because later loads may overwrite previous values.
    Default order:
    1) appdata/config/.env.engine
    2) appdata/config/.env.engine.local
    3) appdata/config/.env.app
    4) appdata/config/.env.app.local
    5) .env.engine (legacy fallback)
    6) .env.engine.local (legacy fallback)
    7) .env.app (legacy fallback)
    8) .env.app.local (legacy fallback)
    """
    to_load = (
        tuple(paths)
        if paths is not None
        else (
            "appdata/config/.env.engine",
            "appdata/config/.env.engine.local",
            "appdata/config/.env.app",
            "appdata/config/.env.app.local",
            ".env.engine",
            ".env.engine.local",
            ".env.app",
            ".env.app.local",
        )
    )
    for path in to_load:
        load_env_file(path, override_existing=override_existing)


def _resolve_env_path(path: str) -> Path:
    """Resolve env path from cwd, frozen exe dir, then project root."""
    candidate = Path(path)
    if candidate.exists():
        return candidate

    if getattr(sys, "frozen", False):
        executable = getattr(sys, "executable", "")
        if executable:
            frozen_dir_candidate = Path(executable).resolve().parent / path
            if frozen_dir_candidate.exists():
                return frozen_dir_candidate

    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        meipass_candidate = Path(str(meipass)) / path
        if meipass_candidate.exists():
            return meipass_candidate

    # Fallback for IDE run configs with different working directory.
    project_root = Path(__file__).resolve().parents[3]
    fallback = project_root / path
    return fallback

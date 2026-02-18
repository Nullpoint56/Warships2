"""Application configuration and env loading."""

from __future__ import annotations

import os
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
    1) .env.engine
    2) .env.engine.local
    3) .env.app
    4) .env.app.local
    """
    to_load = (
        tuple(paths)
        if paths is not None
        else (
            ".env.engine",
            ".env.engine.local",
            ".env.app",
            ".env.app.local",
        )
    )
    for path in to_load:
        load_env_file(path, override_existing=override_existing)


def _resolve_env_path(path: str) -> Path:
    """Resolve env path from cwd first, then project root."""
    candidate = Path(path)
    if candidate.exists():
        return candidate

    # Fallback for IDE run configs with different working directory.
    project_root = Path(__file__).resolve().parents[3]
    fallback = project_root / path
    return fallback

"""Application configuration and env loading."""

from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: str = ".env") -> None:
    """Load KEY=VALUE pairs from an env file into process environment.

    Existing environment variables are not overwritten.
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

        os.environ.setdefault(key, value)


def _resolve_env_path(path: str) -> Path:
    """Resolve env path from cwd first, then project root."""
    candidate = Path(path)
    if candidate.exists():
        return candidate

    # Fallback for IDE run configs with different working directory.
    project_root = Path(__file__).resolve().parents[3]
    fallback = project_root / path
    return fallback

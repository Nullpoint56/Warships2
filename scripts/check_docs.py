#!/usr/bin/env python3
"""Markdown/docs lint checks used by CI and local hooks."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _run_checked(*, label: str, command: list[str], env: dict[str, str]) -> None:
    print(label, flush=True)
    completed = subprocess.run(command, env=env, check=False)
    if completed.returncode != 0:
        raise SystemExit(f"{label} failed with exit code {completed.returncode}.")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)

    env = os.environ.copy()
    env["PYTHONPATH"] = "."

    _run_checked(
        label="Running ruff check --fix for docs/markdown...",
        command=["uv", "run", "ruff", "check", "--fix", "docs", "README.md"],
        env=env,
    )
    _run_checked(
        label="Running ruff format --preview for docs/markdown...",
        command=["uv", "run", "ruff", "format", "--preview", "docs", "README.md"],
        env=env,
    )

    print("Docs markdown checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

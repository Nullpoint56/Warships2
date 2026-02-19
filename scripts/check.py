#!/usr/bin/env python3
"""Cross-platform composite quality checks for local and CI use."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def _run_checked(*, label: str, command: list[str], env: dict[str, str]) -> None:
    print(label, flush=True)
    completed = subprocess.run(command, env=env, check=False)
    if completed.returncode != 0:
        raise SystemExit(f"{label} failed with exit code {completed.returncode}.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run repository quality checks.")
    parser.add_argument("--skip-lint-format-typecheck", action="store_true")
    parser.add_argument("--skip-engine-tests", action="store_true")
    parser.add_argument("--skip-warships-tests", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    os.chdir(root)

    env = os.environ.copy()
    env["PYTHONPATH"] = "."

    if not args.skip_lint_format_typecheck:
        _run_checked(label="Running mypy...", command=["uv", "run", "mypy"], env=env)

    if not args.skip_engine_tests:
        _run_checked(
            label="Running engine tests with coverage gate...",
            command=[
                "uv",
                "run",
                "pytest",
                "tests/engine",
                "--cov=engine",
                "--cov-report=term-missing",
                "--cov-fail-under=75",
            ],
            env=env,
        )

    if not args.skip_warships_tests:
        _run_checked(
            label="Running warships tests with coverage gate...",
            command=[
                "uv",
                "run",
                "pytest",
                "tests/warships",
                "--cov=warships.game",
                "--cov-report=term-missing",
                "--cov-fail-under=75",
            ],
            env=env,
        )
        _run_checked(
            label="Running warships critical coverage gate...",
            command=[
                "uv",
                "run",
                "pytest",
                "tests/warships/unit/core",
                "tests/warships/unit/presets",
                "tests/warships/unit/app/services",
                "--cov=warships.game.core",
                "--cov=warships.game.presets",
                "--cov=warships.game.app.services",
                "--cov-report=term-missing",
                "--cov-fail-under=90",
            ],
            env=env,
        )

    print("All selected checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

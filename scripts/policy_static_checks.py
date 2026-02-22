#!/usr/bin/env python3
"""Run deterministic static policy gates."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _run(label: str, cmd: list[str], env: dict[str, str]) -> int:
    print(label, flush=True)
    resolved_cmd = list(cmd)
    if sys.platform.startswith("win") and resolved_cmd and resolved_cmd[0] == "npx":
        resolved_cmd[0] = "npx.cmd"
    try:
        completed = subprocess.run(resolved_cmd, env=env, check=False)
    except FileNotFoundError:
        print(f"Command not found: {resolved_cmd[0]}")
        return 127
    return int(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run static policy checks.")
    parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    env = os.environ.copy()
    env["PYTHONPATH"] = "."

    checks: list[tuple[str, list[str]]] = [
        (
            "Layered architecture/import contracts (import-linter)",
            ["uv", "run", "lint-imports"],
        ),
        (
            "Bootstrap wiring ownership (only bootstrap may wire concrete implementations)",
            ["uv", "run", "python", "scripts/check_bootstrap_wiring_ownership.py"],
        ),
        (
            "Import cycle gate (SCC size must be 1)",
            ["uv", "run", "python", "scripts/check_import_cycles.py"],
        ),
        (
            "Strict type contracts (mypy --strict)",
            ["uv", "run", "mypy", "--strict"],
        ),
        (
            "Complexity budgets (xenon)",
            ["uv", "run", "xenon", "--max-absolute", "B", "--max-modules", "A", "--max-average", "A", "engine"],
        ),
        (
            "File LOC limits (soft 600 / hard 900)",
            ["uv", "run", "python", "scripts/check_engine_file_limits.py", "--soft", "600", "--hard", "900"],
        ),
        (
            "Broad exception policy (ruff)",
            ["uv", "run", "ruff", "check", "engine", "--select", "E722,BLE001"],
        ),
        (
            "Broad exception policy (semgrep)",
            [
                "uv",
                "run",
                "semgrep",
                "--error",
                "--config",
                "tools/quality/semgrep/broad_exception_policy.yml",
                "engine",
            ],
        ),
        (
            "Domain literal leakage (semgrep)",
            [
                "uv",
                "run",
                "semgrep",
                "--error",
                "--config",
                "tools/quality/semgrep/domain_literal_leakage.yml",
                "engine",
            ],
        ),
        (
            "Duplication threshold (jscpd <= 5%)",
            ["npx", "--yes", "jscpd", "--threshold", "5", "engine"],
        ),
    ]

    failures: list[tuple[str, int]] = []
    for label, cmd in checks:
        exit_code = _run(label, cmd, env)
        if exit_code == 0:
            print(f"[PASS] {label}")
        else:
            print(f"[FAIL] {label} (exit {exit_code})")
            failures.append((label, exit_code))

    print("Deterministic static policy checks completed.")
    if failures:
        print("Failed checks summary:")
        for label, exit_code in failures:
            print(f"  - {label}: exit {exit_code}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

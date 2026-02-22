#!/usr/bin/env python3
"""Run deterministic static policy gates."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def _run(label: str, cmd: list[str], env: dict[str, str]) -> None:
    print(label, flush=True)
    completed = subprocess.run(cmd, env=env, check=False)
    if completed.returncode != 0:
        raise SystemExit(f"{label} failed with exit code {completed.returncode}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run static policy checks.")
    parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    env = os.environ.copy()
    env["PYTHONPATH"] = "."

    _run("Layered architecture/import contracts (import-linter)", ["uv", "run", "lint-imports"], env)
    _run(
        "Bootstrap wiring ownership (only bootstrap may wire concrete implementations)",
        ["uv", "run", "python", "scripts/check_bootstrap_wiring_ownership.py"],
        env,
    )
    _run("Import cycle gate (SCC size must be 1)", ["uv", "run", "python", "scripts/check_import_cycles.py"], env)
    _run("Strict type contracts (mypy --strict)", ["uv", "run", "mypy", "--strict"], env)
    _run(
        "Complexity budgets (xenon)",
        ["uv", "run", "xenon", "--max-absolute", "B", "--max-modules", "A", "--max-average", "A", "engine"],
        env,
    )
    _run(
        "File LOC limits (soft 600 / hard 900)",
        ["uv", "run", "python", "scripts/check_engine_file_limits.py", "--soft", "600", "--hard", "900"],
        env,
    )
    _run(
        "Broad exception policy (ruff)",
        ["uv", "run", "ruff", "check", "engine", "--select", "E722,BLE001"],
        env,
    )
    _run(
        "Broad exception policy (semgrep)",
        ["uv", "run", "semgrep", "--config", "tools/quality/semgrep/broad_exception_policy.yml", "engine"],
        env,
    )
    _run(
        "Domain literal leakage (semgrep)",
        ["uv", "run", "semgrep", "--config", "tools/quality/semgrep/domain_literal_leakage.yml", "engine"],
        env,
    )
    _run(
        "Duplication threshold (jscpd <= 5%)",
        ["npx", "--yes", "jscpd", "--config", ".jscpd.json"],
        env,
    )

    print("Deterministic static policy checks completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
            "API factory runtime-import gate (no create_/run_ runtime imports in engine.api)",
            ["uv", "run", "python", "scripts/check_api_runtime_factories.py"],
        ),
        (
            "Boundary DTO purity gate (no object/Any/runtime annotations in engine.api public contracts)",
            ["uv", "run", "python", "scripts/check_boundary_dto_purity.py"],
        ),
        (
            "Public API surface drift gate (baseline diff)",
            ["uv", "run", "python", "scripts/check_public_api_surface.py"],
        ),
        (
            "Import cycle gate (SCC size must be 1)",
            ["uv", "run", "python", "scripts/check_import_cycles.py"],
        ),
        (
            "Import cycle budget gate (no regression in SCC size/count)",
            [
                "uv",
                "run",
                "python",
                "scripts/check_import_cycles.py",
                "--allow-cycles",
                "--baseline",
                "tools/quality/budgets/import_cycles_baseline.json",
                "--json-output",
                "docs/architecture/audits/static_checks/latest/import_cycles_metrics.json",
            ],
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
            "Barrel export budget gate",
            ["uv", "run", "python", "scripts/check_barrel_exports.py"],
        ),
        (
            "Env read placement gate (env access only in allowed config/bootstrap modules)",
            ["uv", "run", "python", "scripts/check_env_read_placement.py"],
        ),
        (
            "Feature/env flag registry gate (owner/rationale/remove_by/status + expiry)",
            ["uv", "run", "python", "scripts/check_feature_flag_registry.py"],
        ),
        (
            "State mutation ownership gate (no mutable module globals or global writes)",
            ["uv", "run", "python", "scripts/check_state_mutation_ownership.py"],
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
            "Exception observability semantics gate",
            ["uv", "run", "python", "scripts/check_exception_observability.py"],
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
            "Required protocol capability and opaque provider rules (semgrep)",
            [
                "uv",
                "run",
                "semgrep",
                "--error",
                "--config",
                "tools/quality/semgrep/protocol_boundary_rules.yml",
                "engine",
            ],
        ),
        (
            "Domain semantic hardening gate",
            ["uv", "run", "python", "scripts/check_domain_semantic_leakage.py"],
        ),
        (
            "Duplication threshold (jscpd <= 5%)",
            ["npx", "--yes", "jscpd", "--threshold", "5", "engine"],
        ),
        (
            "Duplicate cluster gate (api/ui_primitives vs ui_runtime)",
            ["uv", "run", "python", "scripts/check_duplicate_cluster.py"],
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

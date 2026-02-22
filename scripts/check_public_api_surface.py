#!/usr/bin/env python3
"""Enforce stable public API surface via baseline diff."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path


def _extract_all_symbols(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body if isinstance(tree, ast.Module) else []:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        out: list[str] = []
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                out.append(elt.value)
                        return sorted(set(out))
    return []


def _read_baseline(path: Path) -> list[str]:
    if not path.exists():
        return []
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    return sorted(set(lines))


def _write_baseline(path: Path, symbols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "# Engine API public surface baseline\n" + "\n".join(symbols) + "\n"
    path.write_text(payload, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check public API surface baseline.")
    parser.add_argument("--api-init", default="engine/api/__init__.py")
    parser.add_argument(
        "--baseline",
        default="tools/quality/budgets/engine_api_surface_baseline.txt",
    )
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args()

    api_init = Path(args.api_init)
    baseline_path = Path(args.baseline)
    current = _extract_all_symbols(api_init)

    if args.update_baseline:
        _write_baseline(baseline_path, current)
        print(f"Updated baseline: {baseline_path}")
        return 0

    baseline = _read_baseline(baseline_path)
    if not baseline:
        print(
            f"Baseline not found or empty: {baseline_path}. "
            "Run with --update-baseline to initialize."
        )
        return 1

    added = sorted(set(current) - set(baseline))
    removed = sorted(set(baseline) - set(current))
    if added or removed:
        print("Public API surface drift detected:")
        if added:
            print("  Added symbols:")
            for sym in added:
                print(f"    + {sym}")
        if removed:
            print("  Removed symbols:")
            for sym in removed:
                print(f"    - {sym}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


#!/usr/bin/env python3
"""Enforce barrel export budgets and mixed-layer import hygiene."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path


DEFAULT_BUDGETS = {
    "engine/api/__init__.py": 120,
    "engine/runtime/__init__.py": 30,
}


def _extract_all_count(tree: ast.AST) -> int | None:
    for node in tree.body if isinstance(tree, ast.Module) else []:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        return len(node.value.elts)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Check barrel export budgets.")
    args = parser.parse_args()

    violations: list[str] = []
    for rel_path, budget in DEFAULT_BUDGETS.items():
        path = Path(rel_path)
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        count = _extract_all_count(tree)
        if count is not None and count > budget:
            violations.append(f"{rel_path}: __all__ size {count} exceeds budget {budget}")

        if rel_path == "engine/runtime/__init__.py":
            has_api_import = False
            has_runtime_import = False
            for node in tree.body if isinstance(tree, ast.Module) else []:
                if isinstance(node, ast.ImportFrom):
                    module = str(node.module or "")
                    if module.startswith("engine.api"):
                        has_api_import = True
                    if module.startswith("engine.runtime"):
                        has_runtime_import = True
            if has_api_import and has_runtime_import:
                violations.append(
                    f"{rel_path}: mixed layer barrel imports engine.api.* and engine.runtime.*"
                )

    if violations:
        print("Barrel export budget violations:")
        for line in violations:
            print(f"  {line}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Block runtime concrete imports inside API create_/run_ factory functions."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path


def _is_runtime_import(module: str) -> bool:
    return module == "engine.runtime" or module.startswith("engine.runtime.")


def _check_file(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    violations: list[str] = []

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        name = str(node.name)
        if not (name.startswith("create_") or name.startswith("run_")):
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.Import):
                for alias in inner.names:
                    if _is_runtime_import(alias.name):
                        violations.append(
                            f"{path}:{inner.lineno} function {name} imports {alias.name}"
                        )
            elif isinstance(inner, ast.ImportFrom):
                module = str(inner.module or "")
                if _is_runtime_import(module):
                    violations.append(
                        f"{path}:{inner.lineno} function {name} imports from {module}"
                    )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Check API factory imports.")
    parser.add_argument("--root", default="engine/api")
    args = parser.parse_args()

    root = Path(args.root)
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        violations.extend(_check_file(path))

    if violations:
        print("API runtime factory violations:")
        for line in violations:
            print(f"  {line}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

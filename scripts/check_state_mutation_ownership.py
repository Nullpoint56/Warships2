#!/usr/bin/env python3
"""Guard against mutable module globals and explicit global writes."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path


def _is_mutable_value(node: ast.AST) -> bool:
    if isinstance(node, (ast.List, ast.Dict, ast.Set)):
        return True
    if isinstance(node, ast.Call):
        fn = node.func
        if isinstance(fn, ast.Name) and fn.id in {"list", "dict", "set", "defaultdict", "deque"}:
            return True
    return False


def _module_assignments(tree: ast.Module) -> list[ast.Assign | ast.AnnAssign]:
    out: list[ast.Assign | ast.AnnAssign] = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            out.append(node)
    return out


def _check_file(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    violations: list[str] = []

    for node in _module_assignments(tree):
        if isinstance(node, ast.Assign):
            value = node.value
            if value is None or not _is_mutable_value(value):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id == "__all__":
                        continue
                    violations.append(
                        f"{path}:{node.lineno} module global '{target.id}' initialized with mutable value"
                    )
        elif isinstance(node, ast.AnnAssign):
            if not isinstance(node.target, ast.Name) or node.value is None:
                continue
            if node.target.id == "__all__":
                continue
            if _is_mutable_value(node.value):
                violations.append(
                    f"{path}:{node.lineno} module global '{node.target.id}' initialized with mutable value"
                )

    for node in ast.walk(tree):
        if isinstance(node, ast.Global):
            for name in node.names:
                violations.append(
                    f"{path}:{node.lineno} uses 'global {name}', violating state ownership boundaries"
                )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Check state mutation ownership constraints.")
    parser.add_argument("--root", default="engine")
    args = parser.parse_args()

    root = Path(args.root)
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        violations.extend(_check_file(path))

    if violations:
        print("State mutation ownership violations:")
        for line in violations:
            print(f"  {line}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Restrict env reads to approved config/bootstrap modules."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path


ALLOWED_FILES = {
    "engine/runtime/bootstrap.py",
    "engine/runtime/debug_config.py",
    "engine/diagnostics/config.py",
}


def _is_env_get_call(node: ast.Call) -> bool:
    fn = node.func
    # os.getenv(...)
    if isinstance(fn, ast.Attribute) and fn.attr == "getenv":
        if isinstance(fn.value, ast.Name) and fn.value.id == "os":
            return True
    # os.environ.get(...)
    if isinstance(fn, ast.Attribute) and fn.attr == "get":
        if isinstance(fn.value, ast.Attribute) and fn.value.attr == "environ":
            if isinstance(fn.value.value, ast.Name) and fn.value.value.id == "os":
                return True
    return False


def _check_file(path: Path, rel: str) -> list[str]:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    violations: list[str] = []

    if rel in ALLOWED_FILES:
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_env_get_call(node):
            violations.append(f"{rel}:{node.lineno} env read outside allowed config/bootstrap modules")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Check env read placement.")
    parser.add_argument("--root", default="engine")
    args = parser.parse_args()

    root = Path(args.root)
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        rel = path.as_posix()
        violations.extend(_check_file(path, rel))

    if violations:
        print("Env read placement violations:")
        for line in violations:
            print(f"  {line}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

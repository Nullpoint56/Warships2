#!/usr/bin/env python3
"""Require observability hooks inside broad exception handlers."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path


def _is_broad_exception(handler: ast.ExceptHandler) -> bool:
    typ = handler.type
    if typ is None:
        return True
    if isinstance(typ, ast.Name) and typ.id == "Exception":
        return True
    return False


def _is_truthy(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and bool(node.value) is True


def _is_observability_call(node: ast.Call) -> bool:
    fn = node.func
    if isinstance(fn, ast.Attribute):
        if fn.attr == "exception":
            return True
        if fn.attr in {"error", "warning", "critical"}:
            for kw in node.keywords:
                if kw.arg == "exc_info" and _is_truthy(kw.value):
                    return True
    return False


def _handler_has_observability(handler: ast.ExceptHandler) -> bool:
    for node in ast.walk(ast.Module(body=handler.body, type_ignores=[])):
        if isinstance(node, ast.Call) and _is_observability_call(node):
            return True
    return False


def _check_file(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    violations: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        for handler in node.handlers:
            if not _is_broad_exception(handler):
                continue
            if not _handler_has_observability(handler):
                violations.append(
                    f"{path}:{handler.lineno} broad exception handler lacks logging.exception or logging.*(..., exc_info=True)"
                )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Check exception observability semantics.")
    parser.add_argument("--root", default="engine")
    args = parser.parse_args()

    root = Path(args.root)
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        violations.extend(_check_file(path))

    if violations:
        print("Exception observability violations:")
        for line in violations:
            print(f"  {line}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


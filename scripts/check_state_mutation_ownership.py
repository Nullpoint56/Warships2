#!/usr/bin/env python3
"""Guard against mutable module globals and explicit global writes."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

IMMUTABLE_FACTORY_ALLOWLIST: set[str] = {
    "MappingProxyType",
    "ContextVar",
    "frozenset",
    "tuple",
    "bytes",
    "str",
    "int",
    "float",
    "bool",
    "complex",
}


def _call_name(node: ast.Call) -> str:
    fn = node.func
    if isinstance(fn, ast.Name):
        return fn.id
    if isinstance(fn, ast.Attribute):
        return fn.attr
    return ""


def _is_mutable_value(node: ast.AST) -> bool:
    if isinstance(node, (ast.List, ast.Dict, ast.Set)):
        return True
    if isinstance(node, ast.Call):
        fn_name = _call_name(node)
        if fn_name in {"list", "dict", "set", "defaultdict", "deque"}:
            return True
    return False


def _is_module_singleton_call(
    value: ast.AST,
    *,
    target_name: str,
) -> bool:
    if not isinstance(value, ast.Call):
        return False
    fn_name = _call_name(value)
    if not fn_name or fn_name in IMMUTABLE_FACTORY_ALLOWLIST:
        return False
    # Mutable module singleton pattern: UPPER/private constant target assigned from
    # a class/object constructor call (e.g. _State(), _Probe(), RuntimeService()).
    target_is_singleton_name = target_name.isupper() or target_name.startswith("_")
    if not target_is_singleton_name:
        return False
    if fn_name.startswith("_"):
        return True
    if fn_name and fn_name[0].isupper():
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
                    if _is_mutable_value(value):
                        violations.append(
                            f"{path}:{node.lineno} module global '{target.id}' initialized with mutable value"
                        )
                    elif _is_module_singleton_call(value, target_name=target.id):
                        violations.append(
                            f"{path}:{node.lineno} module global '{target.id}' initialized from singleton object call '{_call_name(value)}(...)'"
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
            elif _is_module_singleton_call(node.value, target_name=node.target.id):
                violations.append(
                    f"{path}:{node.lineno} module global '{node.target.id}' initialized from singleton object call '{_call_name(node.value)}(...)'"
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

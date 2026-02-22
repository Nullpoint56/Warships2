#!/usr/bin/env python3
"""Enforce boundary DTO purity in engine.api."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path


def _ann_text(node: ast.AST | None) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def _is_public_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return not node.name.startswith("_")


def _annotation_is_forbidden(text: str) -> bool:
    lowered = text.replace(" ", "")
    return (
        lowered == "object"
        or lowered == "Any"
        or lowered == "typing.Any"
        or "engine.runtime" in lowered
    )


def _iter_function_nodes(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    nodes: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nodes.append(node)
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    nodes.append(item)
    return nodes


def _check_file(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    violations: list[str] = []

    for fn in _iter_function_nodes(tree):
        if not _is_public_function(fn):
            continue
        for arg in [*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs]:
            text = _ann_text(arg.annotation)
            if text and _annotation_is_forbidden(text):
                violations.append(
                    f"{path}:{arg.lineno} public API parameter '{arg.arg}' uses forbidden annotation '{text}'"
                )
        if fn.args.vararg is not None:
            text = _ann_text(fn.args.vararg.annotation)
            if text and _annotation_is_forbidden(text):
                violations.append(
                    f"{path}:{fn.args.vararg.lineno} public API *{fn.args.vararg.arg} uses forbidden annotation '{text}'"
                )
        if fn.args.kwarg is not None:
            text = _ann_text(fn.args.kwarg.annotation)
            if text and _annotation_is_forbidden(text):
                violations.append(
                    f"{path}:{fn.args.kwarg.lineno} public API **{fn.args.kwarg.arg} uses forbidden annotation '{text}'"
                )
        ret_text = _ann_text(fn.returns)
        if ret_text and _annotation_is_forbidden(ret_text):
            violations.append(
                f"{path}:{fn.lineno} public API return type uses forbidden annotation '{ret_text}'"
            )

    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            if name.startswith("_"):
                continue
            text = _ann_text(node.annotation)
            if text and _annotation_is_forbidden(text):
                violations.append(
                    f"{path}:{node.lineno} public API attribute '{name}' uses forbidden annotation '{text}'"
                )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Check boundary DTO purity.")
    parser.add_argument("--root", default="engine/api")
    args = parser.parse_args()

    root = Path(args.root)
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        violations.extend(_check_file(path))

    if violations:
        print("Boundary DTO purity violations:")
        for line in violations:
            print(f"  {line}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


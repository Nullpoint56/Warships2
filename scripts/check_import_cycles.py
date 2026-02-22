#!/usr/bin/env python3
"""Detect Python import cycles under a package root."""

from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from pathlib import Path


def _module_name(root: Path, file_path: Path) -> str:
    rel = file_path.relative_to(root.parent).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _resolve_import(module: str, level: int, target: str | None) -> str:
    if level == 0:
        return target or ""
    pieces = module.split(".")
    if level > len(pieces):
        return target or ""
    base = pieces[: len(pieces) - level]
    if target:
        base.append(target)
    return ".".join(base)


def _build_graph(root: Path) -> dict[str, set[str]]:
    modules: dict[str, Path] = {}
    for path in sorted(root.rglob("*.py")):
        modules[_module_name(root, path)] = path

    graph: dict[str, set[str]] = defaultdict(set)
    module_names = set(modules.keys())

    for module, path in modules.items():
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported = alias.name
                    for candidate in module_names:
                        if imported == candidate or imported.startswith(f"{candidate}."):
                            graph[module].add(candidate)
            elif isinstance(node, ast.ImportFrom):
                imported = _resolve_import(module, node.level, node.module)
                for candidate in module_names:
                    if imported == candidate or imported.startswith(f"{candidate}."):
                        graph[module].add(candidate)

    for module in module_names:
        graph.setdefault(module, set())
    return graph


def _scc(graph: dict[str, set[str]]) -> list[list[str]]:
    index = 0
    stack: list[str] = []
    in_stack: set[str] = set()
    idx: dict[str, int] = {}
    low: dict[str, int] = {}
    out: list[list[str]] = []

    def strongconnect(v: str) -> None:
        nonlocal index
        idx[v] = index
        low[v] = index
        index += 1
        stack.append(v)
        in_stack.add(v)

        for w in graph[v]:
            if w not in idx:
                strongconnect(w)
                low[v] = min(low[v], low[w])
            elif w in in_stack:
                low[v] = min(low[v], idx[w])

        if low[v] == idx[v]:
            component: list[str] = []
            while True:
                w = stack.pop()
                in_stack.remove(w)
                component.append(w)
                if w == v:
                    break
            out.append(component)

    for v in graph:
        if v not in idx:
            strongconnect(v)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Check import cycles for a package.")
    parser.add_argument("--root", default="engine")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    graph = _build_graph(root)
    components = _scc(graph)
    cycles = [c for c in components if len(c) > 1]
    self_cycles = [m for m, deps in graph.items() if m in deps]

    if cycles or self_cycles:
        print("Import cycles detected:")
        for c in sorted(cycles, key=len, reverse=True):
            print(f"  SCC(size={len(c)}): {', '.join(sorted(c))}")
        for module in sorted(self_cycles):
            print(f"  Self-cycle: {module}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

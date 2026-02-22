#!/usr/bin/env python3
"""Enforce that concrete engine wiring happens only in bootstrap composition module(s)."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path


# Concrete wiring imports that must stay in bootstrap composition.
FORBIDDEN_IMPORT_PREFIXES = (
    "engine.runtime.bootstrap",
    "engine.window.factory",
    "engine.rendering.scene_runtime",
)


def _violations_for_file(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if any(name == p or name.startswith(f"{p}.") for p in FORBIDDEN_IMPORT_PREFIXES):
                    violations.append(
                        f"{path}:{node.lineno} import '{name}' is restricted to bootstrap composition."
                    )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if any(module == p or module.startswith(f"{p}.") for p in FORBIDDEN_IMPORT_PREFIXES):
                violations.append(
                    f"{path}:{node.lineno} from '{module}' import ... is restricted to bootstrap composition."
                )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Check bootstrap-only wiring ownership.")
    parser.add_argument("--root", default="engine")
    args = parser.parse_args()

    root = Path(args.root)
    checked_roots = [root / "api", root / "domain"]
    violations: list[str] = []

    for checked_root in checked_roots:
        if not checked_root.exists():
            continue
        for path in sorted(checked_root.rglob("*.py")):
            violations.extend(_violations_for_file(path))

    if violations:
        print("Bootstrap wiring ownership violations:")
        for line in violations:
            print(f"  {line}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

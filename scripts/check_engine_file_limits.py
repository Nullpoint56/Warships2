#!/usr/bin/env python3
"""Enforce engine file length limits."""

from __future__ import annotations

import argparse
from pathlib import Path


def _count_loc(path: Path) -> int:
    return sum(1 for _ in path.open("r", encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check engine Python file LOC limits.")
    parser.add_argument("--root", default="engine")
    parser.add_argument("--soft", type=int, default=600)
    parser.add_argument("--hard", type=int, default=900)
    args = parser.parse_args()

    root = Path(args.root)
    violations_hard: list[tuple[str, int]] = []
    violations_soft: list[tuple[str, int]] = []

    for path in sorted(root.rglob("*.py")):
        loc = _count_loc(path)
        if loc > args.hard:
            violations_hard.append((str(path), loc))
        elif loc > args.soft:
            violations_soft.append((str(path), loc))

    if violations_soft:
        print("Soft LOC limit exceeded:")
        for path, loc in violations_soft:
            print(f"  {path}: {loc} LOC (soft limit {args.soft})")

    if violations_hard:
        print("Hard LOC limit exceeded:")
        for path, loc in violations_hard:
            print(f"  {path}: {loc} LOC (hard limit {args.hard})")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

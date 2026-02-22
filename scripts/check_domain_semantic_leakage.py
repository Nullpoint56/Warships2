#!/usr/bin/env python3
"""Detect domain-leaning semantics in engine core that are broader than title literals."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATTERNS = [
    re.compile(r'\bif\s+\w+\s*==\s*"primary"\s*:', re.MULTILINE),
    re.compile(r'\bif\s+\w+\s*==\s*"secondary"\s*:', re.MULTILINE),
    re.compile(r"\bgrid_size\s*:\s*int\s*=\s*10\b", re.MULTILINE),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check domain semantic leakage.")
    parser.add_argument("--root", default="engine")
    args = parser.parse_args()

    root = Path(args.root)
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        # ui_runtime may legitimately host app-facing runtime behavior and is handled separately.
        if "engine/ui_runtime/" in path.as_posix():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in PATTERNS:
            for match in pattern.finditer(text):
                lineno = text.count("\n", 0, match.start()) + 1
                violations.append(f"{path.as_posix()}:{lineno} matched /{pattern.pattern}/")

    if violations:
        print("Domain semantic hardening violations:")
        for line in violations:
            print(f"  {line}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

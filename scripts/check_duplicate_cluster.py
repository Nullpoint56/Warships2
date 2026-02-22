#!/usr/bin/env python3
"""Strict duplicate-cluster gate for API UI primitives vs ui_runtime."""

from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Check duplicate cluster gate.")
    parser.parse_args()

    cmd = ["npx", "--yes", "jscpd", "--threshold", "0", "engine/api/ui_primitives.py", "engine/ui_runtime"]
    if sys.platform.startswith("win"):
        cmd[0] = "npx.cmd"
    completed = subprocess.run(cmd, check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())

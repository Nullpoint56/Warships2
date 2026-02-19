from __future__ import annotations

import argparse
from pathlib import Path

from tools.engine_session_inspector.app import run_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="engine_session_inspector")
    parser.add_argument("--version", action="store_true", help="Print tool version")
    parser.add_argument(
        "--logs-root",
        type=Path,
        default=Path("warships/appdata"),
        help="Root directory where run/ui logs are discovered.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.version:
        print("engine_session_inspector v0.2")
        return 0
    return run_app(logs_root=args.logs_root)


if __name__ == "__main__":
    raise SystemExit(main())

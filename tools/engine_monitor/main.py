from __future__ import annotations

import argparse
import os
from pathlib import Path
from tkinter import Tk

from tools.engine_monitor.app import MonitorApp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="engine_monitor")
    parser.add_argument("--version", action="store_true", help="Print tool version")
    parser.add_argument(
        "--logs-root",
        type=Path,
        default=Path("tools/data/logs"),
        help="Logs root path for export/capture compatibility.",
    )
    parser.add_argument(
        "--refresh-ms",
        type=int,
        default=750,
        help="Polling interval in milliseconds.",
    )
    parser.add_argument(
        "--hitch-threshold-ms",
        type=float,
        default=25.0,
        help="Hitch threshold in milliseconds.",
    )
    parser.add_argument(
        "--remote-url",
        type=str,
        default="",
        help="Remote diagnostics endpoint, e.g. http://127.0.0.1:8765",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.version:
        print("engine_monitor v0.1")
        return 0

    root = Tk()
    remote_url = str(args.remote_url).strip() or os.getenv(
        "ENGINE_MONITOR_REMOTE_URL", "http://127.0.0.1:8765"
    )
    MonitorApp(
        root,
        logs_root=Path(args.logs_root),
        refresh_ms=int(args.refresh_ms),
        hitch_threshold_ms=float(args.hitch_threshold_ms),
        remote_url=remote_url,
    )
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

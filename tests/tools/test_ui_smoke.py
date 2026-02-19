from __future__ import annotations

from pathlib import Path
from tkinter import TclError, Tk

import pytest

from tools.engine_monitor.app import MonitorApp
from tools.engine_session_inspector.app import SessionInspectorApp


def _try_create_root() -> Tk | None:
    try:
        root = Tk()
    except TclError:
        return None
    root.withdraw()
    return root


def test_session_inspector_smoke_constructs() -> None:
    root = _try_create_root()
    if root is None:
        pytest.skip("Tk display not available in this environment.")
    try:
        app = SessionInspectorApp(root, logs_root=Path("tools/data/logs"))
        assert app is not None
    finally:
        root.destroy()


def test_engine_monitor_smoke_constructs() -> None:
    root = _try_create_root()
    if root is None:
        pytest.skip("Tk display not available in this environment.")
    try:
        app = MonitorApp(
            root,
            logs_root=Path("tools/data/logs"),
            refresh_ms=1000,
            hitch_threshold_ms=25.0,
            remote_url="http://127.0.0.1:8765",
        )
        assert app is not None
    finally:
        root.destroy()

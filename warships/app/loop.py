"""Application loop bootstrap for the PyQt runtime."""

from __future__ import annotations

import os
import random
from pathlib import Path

from warships.app.controller import GameController
from warships.presets.repository import PresetRepository
from warships.presets.service import PresetService
from warships.qt.window import MainWindow

try:
    from PyQt6.QtWidgets import QApplication
except Exception as exc:  # pragma: no cover
    raise RuntimeError("PyQt6 is required for the UI. Install dependency 'PyQt6'.") from exc


class AppLoop:
    def __init__(self) -> None:
        preset_root = Path(__file__).resolve().parents[1] / "data" / "presets"
        preset_service = PresetService(PresetRepository(preset_root))
        debug_ui = os.getenv("WARSHIPS_DEBUG_UI", "0") == "1"
        self._controller = GameController(preset_service=preset_service, rng=random.Random(), debug_ui=debug_ui)
        self._app = QApplication.instance() or QApplication([])
        self._app.setStyleSheet(
            """
            QWidget { font-size: 16px; }
            QLabel { color: #e2e8f0; }
            QPushButton { padding: 10px 16px; }
            QComboBox { padding: 6px 8px; }
            QListWidget { background: #111827; color: #e5e7eb; }
            """
        )
        self._window = MainWindow(self._controller)

    def run(self) -> None:
        mode = os.getenv("WARSHIPS_WINDOW_MODE", "windowed").lower()
        if mode == "fullscreen":
            self._window.showFullScreen()
        elif mode in {"maximized", "borderless"}:
            self._window.showMaximized()
        else:
            self._window.resize(1280, 800)
            self._window.show()
        self._window.sync_ui()
        self._app.exec()

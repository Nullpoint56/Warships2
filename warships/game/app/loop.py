"""Application loop bootstrap for configured frontend runtime."""

from __future__ import annotations

import os
import random
from pathlib import Path

from warships.game.app.controller import GameController
from warships.game.app.frontend import FrontendWindow
from warships.game.app.frontend_factory import create_frontend
from warships.game.presets.repository import PresetRepository
from warships.game.presets.service import PresetService


class AppLoop:
    def __init__(self) -> None:
        preset_root = Path(__file__).resolve().parents[2] / "data" / "presets"
        preset_service = PresetService(PresetRepository(preset_root))
        debug_ui = os.getenv("WARSHIPS_DEBUG_UI", "0") == "1"
        self._controller = GameController(preset_service=preset_service, rng=random.Random(), debug_ui=debug_ui)
        frontend = create_frontend(self._controller)
        self._window: FrontendWindow = frontend.window
        self._run_event_loop = frontend.run_event_loop

    def run(self) -> None:
        mode = os.getenv("WARSHIPS_WINDOW_MODE", "windowed").lower()
        if mode == "fullscreen":
            self._window.show_fullscreen()
        elif mode in {"maximized", "borderless"}:
            self._window.show_maximized()
        else:
            self._window.show_windowed(1280, 800)
        self._window.sync_ui()
        self._run_event_loop()


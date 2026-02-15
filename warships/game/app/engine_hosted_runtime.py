"""Engine-hosted startup composition for Warships."""

from __future__ import annotations

import os
import random
from pathlib import Path

from engine.input.input_controller import InputController
from engine.rendering.scene import SceneRenderer
from engine.runtime.framework_engine import EngineUIFramework
from engine.runtime.host import EngineHost, EngineHostConfig
from engine.runtime.pygfx_frontend import PygfxFrontendWindow, create_pygfx_window
from engine.ui_runtime.board_layout import BoardLayout
from warships.game.app.controller import GameController
from warships.game.app.engine_adapter import WarshipsAppAdapter
from warships.game.app.engine_game_module import WarshipsGameModule
from warships.game.presets.repository import PresetRepository
from warships.game.presets.service import PresetService
from warships.game.ui.game_view import GameView


def run_engine_hosted_app() -> None:
    """Compose and run Warships on the engine-hosted lifecycle path."""
    controller = _build_controller()
    layout = BoardLayout()
    renderer = SceneRenderer()
    view = GameView(renderer, layout)
    app = WarshipsAppAdapter(controller)
    framework = EngineUIFramework(app=app, renderer=renderer, layout=layout)
    debug_ui = os.getenv("WARSHIPS_DEBUG_UI", "0") == "1"
    module = WarshipsGameModule(
        controller=controller,
        framework=framework,
        view=view,
        debug_ui=debug_ui,
    )
    host = EngineHost(module=module, config=EngineHostConfig())
    input_controller = InputController(on_click_queued=renderer.invalidate)
    input_controller.bind(renderer.canvas)
    window = create_pygfx_window(
        renderer=renderer,
        input_controller=input_controller,
        host=host,
    )

    _apply_window_mode(window)
    window.sync_ui()
    window.run()


def _build_controller() -> GameController:
    preset_root = Path(__file__).resolve().parents[2] / "data" / "presets"
    preset_service = PresetService(PresetRepository(preset_root))
    debug_ui = os.getenv("WARSHIPS_DEBUG_UI", "0") == "1"
    return GameController(preset_service=preset_service, rng=random.Random(), debug_ui=debug_ui)


def _apply_window_mode(window: PygfxFrontendWindow) -> None:
    mode = os.getenv("WARSHIPS_WINDOW_MODE", "windowed").lower()
    if mode == "fullscreen":
        window.show_fullscreen()
        return
    if mode in {"maximized", "borderless"}:
        window.show_maximized()
        return
    window.show_windowed(1280, 800)

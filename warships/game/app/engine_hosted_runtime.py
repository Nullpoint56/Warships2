"""Engine-hosted startup composition for Warships."""

from __future__ import annotations

import os
import random
from pathlib import Path

from engine.api.hosted_runtime import HostedRuntimeConfig, run_pygfx_hosted_runtime
from engine.api.render import RenderAPI
from engine.api.ui_framework import create_ui_framework
from engine.ui_runtime.grid_layout import GridLayout
from warships.game.app.controller import GameController
from warships.game.app.engine_adapter import WarshipsAppAdapter
from warships.game.app.engine_game_module import WarshipsGameModule
from warships.game.presets.repository import PresetRepository
from warships.game.presets.service import PresetService
from warships.game.ui.game_view import GameView


def run_engine_hosted_app() -> None:
    """Compose and run Warships on the engine-hosted lifecycle path."""
    controller = _build_controller()
    debug_ui = os.getenv("WARSHIPS_DEBUG_UI", "0") == "1"
    host_config = HostedRuntimeConfig(window_mode=os.getenv("WARSHIPS_WINDOW_MODE", "windowed"))
    run_pygfx_hosted_runtime(
        module_factory=lambda renderer, layout: _build_module(
            controller, renderer, layout, debug_ui
        ),
        host_config=host_config,
    )


def _build_controller() -> GameController:
    preset_root = Path(__file__).resolve().parents[2] / "data" / "presets"
    preset_service = PresetService(PresetRepository(preset_root))
    debug_ui = os.getenv("WARSHIPS_DEBUG_UI", "0") == "1"
    return GameController(preset_service=preset_service, rng=random.Random(), debug_ui=debug_ui)


def _build_module(
    controller: GameController,
    renderer: RenderAPI,
    layout: GridLayout,
    debug_ui: bool,
) -> WarshipsGameModule:
    view = GameView(renderer, layout)
    app = WarshipsAppAdapter(controller)
    framework = create_ui_framework(app=app, renderer=renderer, layout=layout)
    return WarshipsGameModule(
        controller=controller,
        framework=framework,
        view=view,
        debug_ui=debug_ui,
    )

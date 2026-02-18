"""Engine-owned runtime bootstrap for pygfx host execution."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from engine.api.game_module import GameModule
from engine.api.render import RenderAPI
from engine.api.ui_primitives import GridLayout
from engine.input.input_controller import InputController
from engine.rendering.scene import SceneRenderer
from engine.runtime.host import EngineHost, EngineHostConfig
from engine.runtime.pygfx_frontend import create_pygfx_window


def run_pygfx_hosted_runtime(
    *,
    module_factory: Callable[[RenderAPI, GridLayout], GameModule],
    host_config: EngineHostConfig | None = None,
) -> None:
    """Run engine-hosted pygfx runtime with game module composition callback."""
    layout = GridLayout()
    renderer = SceneRenderer()
    module = module_factory(renderer, layout)
    host = EngineHost(module=module, config=host_config or EngineHostConfig(), render_api=renderer)
    input_controller = InputController(on_click_queued=renderer.invalidate)
    input_controller.bind(renderer.canvas)
    window = create_pygfx_window(renderer=renderer, input_controller=input_controller, host=host)
    _apply_window_mode(window, host.config.window_mode, host.config.width, host.config.height)
    window.sync_ui()
    window.run()


def _apply_window_mode(window: Any, mode: str, width: int, height: int) -> None:
    normalized_mode = mode.strip().lower()
    if normalized_mode == "fullscreen":
        window.show_fullscreen()
        return
    if normalized_mode in {"maximized", "borderless"}:
        window.show_maximized()
        return
    window.show_windowed(width, height)

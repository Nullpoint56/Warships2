"""Engine-owned runtime bootstrap for pygfx host execution."""

from __future__ import annotations

from collections.abc import Callable

from engine.api.game_module import GameModule
from engine.api.render import RenderAPI
from engine.input.input_controller import InputController
from engine.rendering.scene import SceneRenderer
from engine.rendering.scene_runtime import resolve_window_mode
from engine.runtime.host import EngineHost, EngineHostConfig
from engine.runtime.pygfx_frontend import create_pygfx_window
from engine.ui_runtime.board_layout import BoardLayout


def run_pygfx_hosted_runtime(
    *,
    module_factory: Callable[[RenderAPI, BoardLayout], GameModule],
    host_config: EngineHostConfig | None = None,
) -> None:
    """Run engine-hosted pygfx runtime with game module composition callback."""
    layout = BoardLayout()
    renderer = SceneRenderer()
    module = module_factory(renderer, layout)
    host = EngineHost(module=module, config=host_config or EngineHostConfig())
    input_controller = InputController(on_click_queued=renderer.invalidate)
    input_controller.bind(renderer.canvas)
    window = create_pygfx_window(renderer=renderer, input_controller=input_controller, host=host)
    _apply_window_mode(window, host.config.width, host.config.height)
    window.sync_ui()
    window.run()


def _apply_window_mode(window, width: int, height: int) -> None:
    mode = resolve_window_mode()
    if mode == "fullscreen":
        window.show_fullscreen()
        return
    if mode in {"maximized", "borderless"}:
        window.show_maximized()
        return
    window.show_windowed(width, height)

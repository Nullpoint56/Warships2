"""Engine-owned runtime bootstrap for pygfx host execution."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from engine.api.game_module import GameModule
from engine.api.render import RenderAPI
from engine.api.ui_primitives import GridLayout
from engine.input.input_controller import InputController
from engine.rendering.scene import SceneRenderer
from engine.rendering.scene_runtime import resolve_render_loop_config, resolve_render_vsync
from engine.runtime.host import EngineHost, EngineHostConfig
from engine.runtime.logging import setup_engine_logging
from engine.runtime.pygfx_frontend import create_pygfx_window
from engine.window import create_rendercanvas_window


def run_pygfx_hosted_runtime(
    *,
    module_factory: Callable[[RenderAPI, GridLayout], GameModule],
    host_config: EngineHostConfig | None = None,
) -> None:
    """Run engine-hosted pygfx runtime with game module composition callback."""
    setup_engine_logging()
    layout = GridLayout()
    loop_cfg = resolve_render_loop_config()
    vsync = resolve_render_vsync()
    update_mode = "continuous" if loop_cfg.mode == "continuous" else "ondemand"
    max_fps = loop_cfg.fps_cap if loop_cfg.fps_cap > 0.0 else 240.0
    window_layer = create_rendercanvas_window(
        width=1200,
        height=720,
        title="Engine Runtime",
        update_mode=update_mode,
        min_fps=0.0,
        max_fps=float(max_fps),
        vsync=vsync,
    )
    renderer = SceneRenderer(canvas=window_layer.canvas)
    module = module_factory(renderer, layout)
    host = EngineHost(module=module, config=host_config or EngineHostConfig(), render_api=renderer)
    input_controller = InputController(on_click_queued=renderer.invalidate)
    window = create_pygfx_window(
        renderer=renderer,
        window=window_layer,
        input_controller=input_controller,
        host=host,
    )
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

"""Engine-owned runtime bootstrap for hosted execution."""

from __future__ import annotations

import os
import traceback
from collections.abc import Callable
from typing import Any

from engine.api.game_module import GameModule
from engine.api.render import RenderAPI
from engine.api.render_snapshot import RenderSnapshot
from engine.api.ui_primitives import GridLayout
from engine.input.input_controller import InputController
from engine.rendering.scene_runtime import resolve_render_loop_config, resolve_render_vsync
from engine.rendering.wgpu_renderer import WgpuInitError, WgpuRenderer
from engine.runtime.host import EngineHost, EngineHostConfig
from engine.runtime.logging import setup_engine_logging
from engine.runtime.window_frontend import create_window_frontend
from engine.window import create_rendercanvas_window


def run_hosted_runtime(
    *,
    module_factory: Callable[[RenderAPI, GridLayout], GameModule],
    host_config: EngineHostConfig | None = None,
) -> None:
    """Run engine-hosted runtime using window layer + wgpu renderer composition."""
    setup_engine_logging()
    layout = GridLayout()
    config = host_config or EngineHostConfig()
    panel_width, panel_height = _resolve_initial_panel_size(
        fallback_width=int(config.width),
        fallback_height=int(config.height),
    )
    if _resolve_engine_headless():
        renderer: RenderAPI = _HeadlessRenderer()
        module = module_factory(renderer, layout)
        host = EngineHost(module=module, config=config, render_api=renderer)
        while not host.is_closed():
            host.frame()
        return
    loop_cfg = resolve_render_loop_config()
    vsync = resolve_render_vsync()
    update_mode = "continuous" if loop_cfg.mode == "continuous" else "ondemand"
    max_fps = loop_cfg.fps_cap if loop_cfg.fps_cap > 0.0 else 240.0
    window_layer = create_rendercanvas_window(
        width=int(panel_width),
        height=int(panel_height),
        title="Engine Runtime",
        update_mode=update_mode,
        min_fps=0.0,
        max_fps=float(max_fps),
        vsync=vsync,
    )
    surface = window_layer.create_surface()
    try:
        renderer = _create_renderer_for_panel(
            surface=surface,
            panel_width=int(panel_width),
            panel_height=int(panel_height),
        )
    except Exception as exc:
        selected_backend = "unknown"
        adapter_info: dict[str, object] = {}
        if isinstance(exc, WgpuInitError):
            selected_backend = str(exc.details.get("selected_backend", "unknown"))
            raw_info = exc.details.get("adapter_info", {})
            if isinstance(raw_info, dict):
                adapter_info = {str(key): value for key, value in raw_info.items()}
        details = {
            "backend_priority": _resolve_wgpu_backend_priority(),
            "selected_backend": selected_backend,
            "adapter_info": adapter_info,
            "surface_id": str(surface.surface_id),
            "surface_backend": str(surface.backend),
            "surface_provider_type": (
                f"{surface.provider.__class__.__module__}.{surface.provider.__class__.__name__}"
                if surface.provider is not None
                else "none"
            ),
            "attempted_surface_format": "bgra8unorm-srgb",
            "platform": os.name,
            "exception_type": exc.__class__.__name__,
            "exception_message": str(exc),
            "stack": traceback.format_exc(),
        }
        raise RuntimeError(f"wgpu_init_failed details={details!r}") from exc
    module = module_factory(renderer, layout)
    host = EngineHost(module=module, config=config, render_api=renderer)
    input_controller = InputController(on_click_queued=renderer.invalidate)
    window = create_window_frontend(
        renderer=renderer,
        window=window_layer,
        input_controller=input_controller,
        host=host,
    )
    _apply_window_mode(
        window,
        host.config.window_mode,
        int(panel_width),
        int(panel_height),
    )
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


def _resolve_engine_headless() -> bool:
    raw = os.getenv("ENGINE_HEADLESS", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _resolve_wgpu_backend_priority() -> tuple[str, ...]:
    raw = os.getenv("ENGINE_WGPU_BACKENDS", "").strip()
    if not raw:
        return ("vulkan", "metal", "dx12")
    values = tuple(item.strip().lower() for item in raw.split(",") if item.strip())
    return values or ("vulkan", "metal", "dx12")


def _resolve_initial_panel_size(*, fallback_width: int, fallback_height: int) -> tuple[int, int]:
    raw = os.getenv("ENGINE_UI_PANEL_RESOLUTION", "").strip().lower()
    if raw:
        normalized = raw.replace(" ", "")
        for sep in ("x", ",", ":"):
            if sep in normalized:
                left, right = normalized.split(sep, 1)
                try:
                    width = max(1, int(left))
                    height = max(1, int(right))
                except ValueError:
                    break
                return (width, height)
    return (max(1, int(fallback_width)), max(1, int(fallback_height)))


class _HeadlessRenderer(RenderAPI):
    """RenderAPI implementation for headless runtime execution."""

    def begin_frame(self) -> None:
        return

    def end_frame(self) -> None:
        return

    def add_rect(
        self,
        key: str | None,
        x: float,
        y: float,
        w: float,
        h: float,
        color: str,
        z: float = 0.0,
        static: bool = False,
    ) -> None:
        _ = (key, x, y, w, h, color, z, static)
        return

    def add_style_rect(
        self,
        *,
        style_kind: str,
        key: str,
        x: float,
        y: float,
        w: float,
        h: float,
        color: str,
        z: float = 0.0,
        static: bool = False,
        radius: float = 0.0,
        thickness: float = 1.0,
        color_secondary: str = "",
    ) -> None:
        _ = (
            style_kind,
            key,
            x,
            y,
            w,
            h,
            color,
            z,
            static,
            radius,
            thickness,
            color_secondary,
        )
        return

    def add_grid(
        self,
        key: str,
        x: float,
        y: float,
        width: float,
        height: float,
        lines: int,
        color: str,
        z: float = 0.5,
        static: bool = False,
    ) -> None:
        _ = (key, x, y, width, height, lines, color, z, static)
        return

    def add_text(
        self,
        key: str | None,
        text: str,
        x: float,
        y: float,
        font_size: float = 18.0,
        color: str = "#ffffff",
        anchor: str = "top-left",
        z: float = 2.0,
        static: bool = False,
    ) -> None:
        _ = (key, text, x, y, font_size, color, anchor, z, static)
        return

    def set_title(self, title: str) -> None:
        _ = title
        return

    def fill_window(self, key: str, color: str, z: float = -100.0) -> None:
        _ = (key, color, z)
        return

    def to_design_space(self, x: float, y: float) -> tuple[float, float]:
        return (float(x), float(y))

    def invalidate(self) -> None:
        return

    def run(self, draw_callback: Callable[[], None]) -> None:
        _ = draw_callback
        return

    def close(self) -> None:
        return

    def render_snapshot(self, snapshot: RenderSnapshot) -> None:
        _ = snapshot
        return


def _create_renderer_for_panel(
    *,
    surface: Any,
    panel_width: int,
    panel_height: int,
) -> RenderAPI:
    try:
        return WgpuRenderer(
            surface=surface,
            width=int(panel_width),
            height=int(panel_height),
        )
    except TypeError:
        return WgpuRenderer(surface=surface)

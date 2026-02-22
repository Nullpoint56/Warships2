"""Runtime/bootstrap helpers for rendercanvas-backed scene rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.runtime.config import RuntimeConfig, get_runtime_config
from engine.window.rendercanvas_glfw import (
    apply_startup_window_mode as _apply_startup_window_mode,
    run_backend_loop as _run_backend_loop,
    stop_backend_loop as _stop_backend_loop,
)


@dataclass(frozen=True, slots=True)
class RenderLoopConfig:
    """Runtime render loop capability configuration."""

    mode: str = "on_demand"
    fps_cap: float = 60.0


def resolve_render_vsync(config: RuntimeConfig | None = None) -> bool:
    """Resolve render present sync policy from centralized runtime config."""
    runtime_config = config or get_runtime_config()
    return bool(runtime_config.render.vsync)


def resolve_render_loop_config(config: RuntimeConfig | None = None) -> RenderLoopConfig:
    """Resolve render loop capability settings from centralized runtime config."""
    runtime_config = config or get_runtime_config()
    mode = runtime_config.render.loop_mode
    fps_cap = runtime_config.render.fps_cap
    return RenderLoopConfig(
        mode=mode,
        fps_cap=max(0.0, fps_cap),
    )


def resolve_preserve_aspect(config: RuntimeConfig | None = None) -> bool:
    """Resolve preserve-aspect behavior from centralized runtime config."""
    runtime_config = config or get_runtime_config()
    return bool(runtime_config.render.preserve_aspect)


def resolve_window_mode(config: RuntimeConfig | None = None) -> str:
    """Resolve startup window mode from centralized runtime config."""
    runtime_config = config or get_runtime_config()
    return str(runtime_config.render.window_mode)


def apply_startup_window_mode(canvas: Any, window_mode: str) -> None:
    """Compatibility wrapper to the window subsystem startup mode helper."""
    _apply_startup_window_mode(canvas, window_mode)


def get_canvas_logical_size(canvas: Any) -> tuple[float, float] | None:
    """Read logical canvas size from backend in a tolerant way."""
    get_logical_size = getattr(canvas, "get_logical_size", None)
    if not callable(get_logical_size):
        return None
    try:
        size = get_logical_size()
    except Exception:
        return None
    if not (isinstance(size, (tuple, list)) and len(size) >= 2):
        return None
    width, height = size[0], size[1]
    if not isinstance(width, (int, float)) or not isinstance(height, (int, float)):
        return None
    return float(width), float(height)


def run_backend_loop(rc_auto: Any) -> None:
    """Compatibility wrapper to the window subsystem backend loop runner."""
    _run_backend_loop(rc_auto)


def stop_backend_loop(rc_auto: Any) -> None:
    """Compatibility wrapper to the window subsystem backend loop stopper."""
    _stop_backend_loop(rc_auto)

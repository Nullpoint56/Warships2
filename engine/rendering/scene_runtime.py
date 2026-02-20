"""Runtime/bootstrap helpers for rendercanvas-backed scene rendering."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

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
    resize_cooldown_ms: int = 250


def resolve_render_vsync() -> bool:
    """Read render present sync policy from environment."""
    raw = os.getenv("ENGINE_RENDER_VSYNC", "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def resolve_render_loop_config() -> RenderLoopConfig:
    """Read render loop capability settings from environment."""
    mode = os.getenv("ENGINE_RENDER_LOOP_MODE", "on_demand").strip().lower()
    if mode not in {"on_demand", "continuous", "continuous_during_resize"}:
        mode = "on_demand"
    try:
        fps_cap = float(os.getenv("ENGINE_RENDER_FPS_CAP", "60.0"))
    except ValueError:
        fps_cap = 60.0
    try:
        resize_cooldown_ms = int(os.getenv("ENGINE_RENDER_RESIZE_COOLDOWN_MS", "250"))
    except ValueError:
        resize_cooldown_ms = 250
    return RenderLoopConfig(
        mode=mode,
        fps_cap=max(0.0, fps_cap),
        resize_cooldown_ms=max(0, resize_cooldown_ms),
    )


def resolve_preserve_aspect() -> bool:
    """Read aspect mode from env and normalize into preserve_aspect flag."""
    aspect_mode = os.getenv("ENGINE_UI_ASPECT_MODE", "contain").strip().lower()
    return aspect_mode in {"contain", "preserve", "fixed"}


def resolve_window_mode() -> str:
    """Read startup window mode from environment."""
    return os.getenv("ENGINE_WINDOW_MODE", "windowed").strip().lower()


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

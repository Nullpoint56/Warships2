"""Runtime/bootstrap helpers for rendercanvas-backed scene rendering."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from engine.runtime_profile import resolve_runtime_profile
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


def resolve_render_vsync() -> bool:
    """Read render present sync policy from environment."""
    profile = resolve_runtime_profile()
    raw = os.getenv("ENGINE_RENDER_VSYNC", "1" if profile.render_vsync else "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def resolve_render_loop_config() -> RenderLoopConfig:
    """Read render loop capability settings from environment."""
    profile = resolve_runtime_profile()
    mode = os.getenv("ENGINE_RENDER_LOOP_MODE", profile.render_loop_mode).strip().lower()
    if mode not in {"on_demand", "continuous"}:
        mode = profile.render_loop_mode
    try:
        fps_cap = float(os.getenv("ENGINE_RENDER_FPS_CAP", str(profile.render_fps_cap)))
    except ValueError:
        fps_cap = profile.render_fps_cap
    return RenderLoopConfig(
        mode=mode,
        fps_cap=max(0.0, fps_cap),
    )


def resolve_preserve_aspect() -> bool:
    """Read aspect mode from env and normalize into preserve_aspect flag."""
    aspect_mode = os.getenv("ENGINE_UI_ASPECT_MODE", "stretch").strip().lower()
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

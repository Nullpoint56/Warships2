"""Runtime/bootstrap helpers for rendercanvas-backed scene rendering."""

from __future__ import annotations

import os
from typing import Any


def resolve_preserve_aspect() -> bool:
    """Read aspect mode from env and normalize into preserve_aspect flag."""
    aspect_mode = os.getenv(
        "ENGINE_UI_ASPECT_MODE", os.getenv("WARSHIPS_UI_ASPECT_MODE", "contain")
    ).strip().lower()
    return aspect_mode in {"contain", "preserve", "fixed"}


def resolve_window_mode() -> str:
    """Read startup window mode from environment."""
    return os.getenv(
        "ENGINE_WINDOW_MODE", os.getenv("WARSHIPS_WINDOW_MODE", "windowed")
    ).strip().lower()


def apply_startup_window_mode(canvas: Any, window_mode: str) -> None:
    """Set startup window mode for GLFW backend when available."""
    try:
        import rendercanvas.glfw as rc_glfw
    except Exception:
        return
    window = getattr(canvas, "_window", None)
    if window is None:
        return
    glfw = rc_glfw.glfw
    try:
        glfw.set_window_attrib(window, glfw.RESIZABLE, glfw.FALSE)
    except Exception:
        pass
    if window_mode == "maximized":
        try:
            glfw.maximize_window(window)
        except Exception:
            pass
        return
    monitor = glfw.get_primary_monitor()
    if not monitor:
        try:
            glfw.maximize_window(window)
        except Exception:
            pass
        return
    if window_mode == "fullscreen":
        video_mode = glfw.get_video_mode(monitor)
        if video_mode is not None:
            try:
                glfw.set_window_monitor(
                    window,
                    monitor,
                    0,
                    0,
                    int(video_mode.size.width),
                    int(video_mode.size.height),
                    int(video_mode.refresh_rate),
                )
                return
            except Exception:
                pass
    try:
        x, y, w, h = glfw.get_monitor_workarea(monitor)
        glfw.set_window_monitor(window, None, int(x), int(y), int(w), int(h), 0)
    except Exception:
        try:
            glfw.maximize_window(window)
        except Exception:
            pass


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
    """Run rendercanvas loop entrypoint."""
    loop = getattr(rc_auto, "loop", None)
    if loop is not None and hasattr(loop, "run"):
        loop.run()
        return
    run_func = getattr(rc_auto, "run", None)
    if callable(run_func):
        run_func()
        return
    raise RuntimeError("rendercanvas.auto did not expose a runnable loop.")


def stop_backend_loop(rc_auto: Any) -> None:
    """Stop rendercanvas loop when supported."""
    loop = getattr(rc_auto, "loop", None)
    if loop is not None and hasattr(loop, "stop"):
        loop.stop()

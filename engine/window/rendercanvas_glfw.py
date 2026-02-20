"""Rendercanvas/GLFW-backed window layer implementation."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from engine.api.window import (
    SurfaceHandle,
    WindowCloseEvent,
    WindowEvent,
    WindowFocusEvent,
    WindowMinimizeEvent,
    WindowPort,
    WindowResizeEvent,
)


def apply_startup_window_mode(canvas: Any, window_mode: str) -> None:
    """Apply startup mode via GLFW when backend internals are available."""
    try:
        import rendercanvas.glfw as rc_glfw
    except Exception:
        return
    window = getattr(canvas, "_window", None)
    if window is None:
        return
    glfw = rc_glfw.glfw
    mode = window_mode.strip().lower()

    if mode == "maximized":
        try:
            glfw.set_window_attrib(window, glfw.RESIZABLE, glfw.TRUE)
        except Exception:
            pass
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
    if mode == "fullscreen":
        try:
            glfw.set_window_attrib(window, glfw.RESIZABLE, glfw.FALSE)
        except Exception:
            pass
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
        return

    if mode == "borderless":
        try:
            glfw.set_window_attrib(window, glfw.RESIZABLE, glfw.FALSE)
        except Exception:
            pass
        try:
            x, y, w, h = glfw.get_monitor_workarea(monitor)
            glfw.set_window_monitor(window, None, int(x), int(y), int(w), int(h), 0)
            return
        except Exception:
            try:
                glfw.maximize_window(window)
            except Exception:
                pass
        return

    try:
        glfw.set_window_attrib(window, glfw.RESIZABLE, glfw.TRUE)
    except Exception:
        pass


def run_backend_loop(rc_auto: Any) -> None:
    """Run rendercanvas backend loop."""
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
    """Stop rendercanvas backend loop when supported."""
    loop = getattr(rc_auto, "loop", None)
    if loop is not None and hasattr(loop, "stop"):
        loop.stop()


@dataclass(slots=True)
class RenderCanvasWindow(WindowPort):
    """Window-layer adapter over an existing rendercanvas canvas."""

    canvas: Any
    backend: str = "rendercanvas.glfw"
    _events: deque[WindowEvent] = field(default_factory=deque)

    def __post_init__(self) -> None:
        self._bind_window_events()

    def create_surface(self) -> SurfaceHandle:
        return SurfaceHandle(surface_id=f"{id(self.canvas)}", backend=self.backend)

    def poll_events(self) -> tuple[WindowEvent, ...]:
        drained = tuple(self._events)
        self._events.clear()
        return drained

    def set_title(self, title: str) -> None:
        setter = getattr(self.canvas, "set_title", None)
        if callable(setter):
            setter(title)

    def set_windowed(self, width: int, height: int) -> None:
        apply_startup_window_mode(self.canvas, "windowed")
        setter = getattr(self.canvas, "set_logical_size", None)
        if callable(setter):
            setter(width, height)

    def set_fullscreen(self) -> None:
        apply_startup_window_mode(self.canvas, "fullscreen")

    def set_maximized(self) -> None:
        apply_startup_window_mode(self.canvas, "maximized")

    def close(self) -> None:
        closer = getattr(self.canvas, "close", None)
        if callable(closer):
            closer()

    def _bind_window_events(self) -> None:
        add_handler = getattr(self.canvas, "add_event_handler", None)
        if not callable(add_handler):
            return
        try:
            add_handler(self._on_resize, "resize")
            add_handler(self._on_close, "close")
            add_handler(self._on_minimize, "minimize")
            add_handler(self._on_focus, "focus")
        except Exception:
            return

    def _on_resize(self, event: object) -> None:
        if not isinstance(event, dict):
            return
        size = event.get("size")
        if not (isinstance(size, (tuple, list)) and len(size) >= 2):
            return
        lw, lh = size[0], size[1]
        if not isinstance(lw, (int, float)) or not isinstance(lh, (int, float)):
            return
        ratio_raw = event.get("pixel_ratio", 1.0)
        dpi_scale = float(ratio_raw) if isinstance(ratio_raw, (int, float)) and ratio_raw > 0 else 1.0
        self._events.append(
            WindowResizeEvent(
                logical_width=float(lw),
                logical_height=float(lh),
                physical_width=max(1, int(float(lw) * dpi_scale)),
                physical_height=max(1, int(float(lh) * dpi_scale)),
                dpi_scale=dpi_scale,
            )
        )

    def _on_focus(self, event: object) -> None:
        if not isinstance(event, dict):
            return
        focused = event.get("focused")
        if isinstance(focused, bool):
            self._events.append(WindowFocusEvent(focused=focused))

    def _on_minimize(self, event: object) -> None:
        if not isinstance(event, dict):
            return
        minimized = event.get("minimized")
        if isinstance(minimized, bool):
            self._events.append(WindowMinimizeEvent(minimized=minimized))

    def _on_close(self, event: object) -> None:
        _ = event
        self._events.append(WindowCloseEvent())


def create_rendercanvas_window(canvas: Any) -> RenderCanvasWindow:
    """Create window adapter over an existing rendercanvas canvas."""
    return RenderCanvasWindow(canvas=canvas)


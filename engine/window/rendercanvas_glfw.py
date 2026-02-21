"""Rendercanvas/GLFW-backed window layer implementation."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import logging
import os
from typing import Any

from engine.api.input_events import KeyEvent, PointerEvent, WheelEvent
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
    _input_events: deque[PointerEvent | KeyEvent | WheelEvent] = field(default_factory=deque)
    _rc_auto: Any | None = field(default=None, repr=False)
    _debug_events: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        self._debug_events = (
            os.getenv("ENGINE_WINDOW_EVENTS_TRACE_ENABLED", "0").strip().lower()
            in {"1", "true", "yes", "on"}
        )
        if self._rc_auto is None:
            try:
                import rendercanvas.auto as rc_auto
            except Exception:
                rc_auto = None
            self._rc_auto = rc_auto
        self._bind_window_events()

    def create_surface(self) -> SurfaceHandle:
        return SurfaceHandle(surface_id=f"{id(self.canvas)}", backend=self.backend, provider=self.canvas)

    def poll_events(self) -> tuple[WindowEvent, ...]:
        drained = tuple(self._events)
        self._events.clear()
        return drained

    def poll_input_events(self) -> tuple[PointerEvent | KeyEvent | WheelEvent, ...]:
        drained = tuple(self._input_events)
        self._input_events.clear()
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
        self.stop_loop()
        closer = getattr(self.canvas, "close", None)
        if callable(closer):
            closer()

    def run_loop(self) -> None:
        if self._rc_auto is None:
            return
        run_backend_loop(self._rc_auto)

    def stop_loop(self) -> None:
        if self._rc_auto is None:
            return
        stop_backend_loop(self._rc_auto)

    def _bind_window_events(self) -> None:
        add_handler = getattr(self.canvas, "add_event_handler", None)
        if not callable(add_handler):
            return
        self._try_add_event_handler(add_handler, self._on_resize, "resize")
        self._try_add_event_handler(add_handler, self._on_close, "close")
        self._try_add_event_handler(add_handler, self._on_minimize, "minimize")
        self._try_add_event_handler(add_handler, self._on_focus, "focus")
        self._try_add_event_handler(add_handler, self._on_pointer_down, "pointer_down")
        self._try_add_event_handler(add_handler, self._on_pointer_move, "pointer_move")
        self._try_add_event_handler(add_handler, self._on_pointer_up, "pointer_up")
        self._try_add_event_handler(add_handler, self._on_pointer_down, "mouse_down")
        self._try_add_event_handler(add_handler, self._on_pointer_move, "mouse_move")
        self._try_add_event_handler(add_handler, self._on_pointer_up, "mouse_up")
        self._try_add_event_handler(add_handler, self._on_key_down, "key_down")
        self._try_add_event_handler(add_handler, self._on_key_up, "key_up")
        self._try_add_event_handler(add_handler, self._on_char, "char")
        self._try_add_event_handler(add_handler, self._on_wheel, "wheel")
        if self._debug_events:
            self._try_add_event_handler(add_handler, self._on_any_event, "*")

    def _on_resize(self, event: object) -> None:
        size = _event_value(event, "size")
        lw: object | None = None
        lh: object | None = None
        if isinstance(size, (tuple, list)) and len(size) >= 2:
            lw, lh = size[0], size[1]
        else:
            lw = _event_value(event, "width")
            lh = _event_value(event, "height")
            if not isinstance(lw, (int, float)) or not isinstance(lh, (int, float)):
                logical_size = _event_value(event, "logical_size")
                if isinstance(logical_size, (tuple, list)) and len(logical_size) >= 2:
                    lw, lh = logical_size[0], logical_size[1]
                else:
                    return
        if not isinstance(lw, (int, float)) or not isinstance(lh, (int, float)):
            return
        ratio_raw = _event_value(event, "pixel_ratio", 1.0)
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
        self._request_redraw()

    def _on_focus(self, event: object) -> None:
        focused = _event_value(event, "focused")
        if isinstance(focused, bool):
            self._events.append(WindowFocusEvent(focused=focused))
            self._request_redraw()

    def _on_minimize(self, event: object) -> None:
        minimized = _event_value(event, "minimized")
        if isinstance(minimized, bool):
            self._events.append(WindowMinimizeEvent(minimized=minimized))
            self._request_redraw()

    def _on_close(self, event: object) -> None:
        _ = event
        self._events.append(WindowCloseEvent())
        self._request_redraw()

    def _on_pointer_down(self, event: object) -> None:
        parsed = _parse_pointer_event(event, expected_type="pointer_down")
        if parsed is not None:
            self._input_events.append(parsed)
            self._request_redraw()

    def _on_pointer_move(self, event: object) -> None:
        parsed = _parse_pointer_event(event, expected_type="pointer_move")
        if parsed is not None:
            self._input_events.append(parsed)
            self._request_redraw()

    def _on_pointer_up(self, event: object) -> None:
        parsed = _parse_pointer_event(event, expected_type="pointer_up")
        if parsed is not None:
            self._input_events.append(parsed)
            self._request_redraw()

    def _on_key_down(self, event: object) -> None:
        parsed = _parse_key_event(event, expected_type="key_down")
        if parsed is not None:
            self._input_events.append(parsed)
            self._request_redraw()

    def _on_key_up(self, event: object) -> None:
        parsed = _parse_key_event(event, expected_type="key_up")
        if parsed is not None:
            self._input_events.append(parsed)
            self._request_redraw()

    def _on_char(self, event: object) -> None:
        parsed = _parse_char_event(event)
        if parsed is not None:
            self._input_events.append(parsed)
            self._request_redraw()

    def _on_wheel(self, event: object) -> None:
        parsed = _parse_wheel_event(event)
        if parsed is not None:
            self._input_events.append(parsed)
            self._request_redraw()

    def _request_redraw(self) -> None:
        request_draw = getattr(self.canvas, "request_draw", None)
        if callable(request_draw):
            try:
                request_draw()
            except TypeError:
                return

    def _try_add_event_handler(self, add_handler: Any, handler: Any, event_type: str) -> None:
        try:
            add_handler(handler, event_type)
        except Exception:
            return

    def _on_any_event(self, event: object) -> None:
        if not self._debug_events:
            return
        event_type = str(_event_value(event, "event_type", ""))
        if event_type == "before_draw":
            return
        _LOG.debug("window_event type=%s payload=%r", event_type, event)


def create_rendercanvas_window(
    canvas: Any | None = None,
    *,
    width: int = 1200,
    height: int = 720,
    title: str = "Engine Runtime",
    update_mode: str = "ondemand",
    min_fps: float = 0.0,
    max_fps: float = 240.0,
    vsync: bool = True,
) -> RenderCanvasWindow:
    """Create window adapter over an existing or newly created rendercanvas canvas."""
    _install_wgpu_physical_size_guard()
    if canvas is not None:
        return RenderCanvasWindow(canvas=canvas)
    try:
        import rendercanvas.auto as rc_auto
    except Exception as exc:
        raise RuntimeError(
            "Render canvas backend unavailable. Install a desktop backend such as glfw or pyside6."
        ) from exc
    canvas_cls = getattr(rc_auto, "RenderCanvas", None)
    if canvas_cls is None:
        raise RuntimeError("rendercanvas.auto did not expose RenderCanvas.")
    try:
        canvas = canvas_cls(
            size=(int(width), int(height)),
            title=title,
            update_mode=update_mode,
            min_fps=float(min_fps),
            max_fps=float(max_fps),
            vsync=bool(vsync),
        )
    except TypeError:
        canvas = canvas_cls(size=(int(width), int(height)), title=title)
    return RenderCanvasWindow(canvas=canvas, _rc_auto=rc_auto)


def _parse_pointer_event(event: object, *, expected_type: str) -> PointerEvent | None:
    raw_type = str(_event_value(event, "event_type", "")).strip().lower()
    if not _is_pointer_type_match(raw_type, expected_type):
        return None
    x = _event_value(event, "x")
    y = _event_value(event, "y")
    button = _event_value(event, "button", 0)
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return None
    if not isinstance(button, int):
        button = 0
    if expected_type in {"pointer_down", "pointer_up"} and int(button) == 0:
        button = 1
    return PointerEvent(expected_type, float(x), float(y), int(button))


def _parse_key_event(event: object, *, expected_type: str) -> KeyEvent | None:
    if str(_event_value(event, "event_type", "")) != expected_type:
        return None
    key = _event_value(event, "key")
    if not isinstance(key, str):
        return None
    return KeyEvent(expected_type, key)


def _parse_char_event(event: object) -> KeyEvent | None:
    if str(_event_value(event, "event_type", "")) != "char":
        return None
    value = _event_value(event, "data")
    if not isinstance(value, str):
        return None
    return KeyEvent("char", value)


def _parse_wheel_event(event: object) -> WheelEvent | None:
    if str(_event_value(event, "event_type", "")) != "wheel":
        return None
    x = _event_value(event, "x")
    y = _event_value(event, "y")
    dy = _event_value(event, "dy")
    if (
        not isinstance(x, (int, float))
        or not isinstance(y, (int, float))
        or not isinstance(dy, (int, float))
    ):
        return None
    return WheelEvent(float(x), float(y), float(dy))


def _event_value(event: object, key: str, default: object | None = None) -> object | None:
    if isinstance(event, dict):
        return event.get(key, default)
    return getattr(event, key, default)


def _is_pointer_type_match(raw_type: str, expected_type: str) -> bool:
    aliases: dict[str, tuple[str, ...]] = {
        "pointer_down": ("pointer_down", "mouse_down"),
        "pointer_move": ("pointer_move", "mouse_move"),
        "pointer_up": ("pointer_up", "mouse_up"),
    }
    allowed = aliases.get(expected_type, (expected_type,))
    return raw_type in allowed


def _install_wgpu_physical_size_guard() -> None:
    """Clamp non-positive physical resize values to avoid backend resize crashes."""
    try:
        from wgpu import _classes as wgpu_classes
    except Exception:
        return
    target_cls = getattr(wgpu_classes, "GPUCanvasContext", None)
    if target_cls is None:
        return
    original = getattr(target_cls, "set_physical_size", None)
    if not callable(original):
        return
    if getattr(target_cls, "_engine_physical_size_guard_installed", False):
        return

    def _guarded_set_physical_size(self: object, width: int, height: int) -> None:
        safe_w = max(1, int(width))
        safe_h = max(1, int(height))
        original(self, safe_w, safe_h)

    setattr(target_cls, "set_physical_size", _guarded_set_physical_size)
    setattr(target_cls, "_engine_physical_size_guard_installed", True)


_LOG = logging.getLogger("engine.window")

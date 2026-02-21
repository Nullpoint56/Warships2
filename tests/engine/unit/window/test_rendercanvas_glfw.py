from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from engine.api.window import (
    WindowCloseEvent,
    WindowFocusEvent,
    WindowMinimizeEvent,
    WindowResizeEvent,
)
from engine.api.input_events import KeyEvent, PointerEvent, WheelEvent
from engine.window.rendercanvas_glfw import (
    RenderCanvasWindow,
    apply_startup_window_mode,
    create_rendercanvas_window,
    run_backend_loop,
    stop_backend_loop,
)


class _FakeGlfw:
    FALSE = 0
    TRUE = 1
    RESIZABLE = 1

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.monitor = object()
        self.video_mode = SimpleNamespace(
            size=SimpleNamespace(width=1920, height=1080), refresh_rate=60
        )

    def set_window_attrib(self, window, attr, value) -> None:
        _ = (window, attr, value)
        self.calls.append("set_window_attrib")

    def maximize_window(self, window) -> None:
        _ = window
        self.calls.append("maximize_window")

    def get_primary_monitor(self):
        return self.monitor

    def get_video_mode(self, monitor):
        _ = monitor
        return self.video_mode

    def set_window_monitor(self, *args) -> None:
        _ = args
        self.calls.append("set_window_monitor")

    def get_monitor_workarea(self, monitor):
        _ = monitor
        return (1, 2, 3, 4)


def _install_fake_rendercanvas_glfw(monkeypatch: pytest.MonkeyPatch, glfw_obj: _FakeGlfw) -> None:
    rendercanvas_mod = ModuleType("rendercanvas")
    glfw_mod = ModuleType("rendercanvas.glfw")
    glfw_mod.glfw = glfw_obj
    rendercanvas_mod.glfw = glfw_mod
    monkeypatch.setitem(sys.modules, "rendercanvas", rendercanvas_mod)
    monkeypatch.setitem(sys.modules, "rendercanvas.glfw", glfw_mod)


class _Loop:
    def __init__(self) -> None:
        self.ran = 0
        self.stopped = 0

    def run(self) -> None:
        self.ran += 1

    def stop(self) -> None:
        self.stopped += 1


class _AutoWithLoop:
    def __init__(self) -> None:
        self.loop = _Loop()


class _AutoWithRun:
    def __init__(self) -> None:
        self.ran = 0

    def run(self) -> None:
        self.ran += 1


class _Canvas:
    def __init__(self) -> None:
        self._window = object()
        self.handlers: dict[str, list] = {}
        self.set_size_calls: list[tuple[int, int]] = []
        self.titles: list[str] = []
        self.closed = 0
        self.request_draw_calls = 0

    def add_event_handler(self, handler, event_type: str) -> None:
        self.handlers.setdefault(event_type, []).append(handler)

    def set_logical_size(self, width: int, height: int) -> None:
        self.set_size_calls.append((width, height))

    def set_title(self, title: str) -> None:
        self.titles.append(title)

    def close(self) -> None:
        self.closed += 1

    def request_draw(self, *args) -> None:
        _ = args
        self.request_draw_calls += 1

    def emit(self, event_type: str, **payload) -> None:
        event = {"event_type": event_type, **payload}
        for handler in self.handlers.get(event_type, []):
            handler(event)

    def emit_obj(self, event_type: str, **payload) -> None:
        event = SimpleNamespace(event_type=event_type, **payload)
        for handler in self.handlers.get(event_type, []):
            handler(event)


class _StrictCanvas(_Canvas):
    _valid_event_types = {
        "animate",
        "before_draw",
        "char",
        "close",
        "double_click",
        "key_down",
        "key_up",
        "pointer_down",
        "pointer_enter",
        "pointer_leave",
        "pointer_move",
        "pointer_up",
        "resize",
        "wheel",
        "*",
    }

    def add_event_handler(self, handler, event_type: str) -> None:
        if event_type not in self._valid_event_types:
            raise ValueError(f"invalid event type: {event_type}")
        super().add_event_handler(handler, event_type)


def test_apply_startup_window_mode_fullscreen(monkeypatch: pytest.MonkeyPatch) -> None:
    glfw = _FakeGlfw()
    _install_fake_rendercanvas_glfw(monkeypatch, glfw)
    apply_startup_window_mode(SimpleNamespace(_window=object()), "fullscreen")
    assert "set_window_monitor" in glfw.calls


def test_run_and_stop_backend_loop_helpers() -> None:
    with_loop = _AutoWithLoop()
    run_backend_loop(with_loop)
    assert with_loop.loop.ran == 1
    stop_backend_loop(with_loop)
    assert with_loop.loop.stopped == 1

    with_run = _AutoWithRun()
    run_backend_loop(with_run)
    assert with_run.ran == 1


def test_run_backend_loop_raises_when_no_entrypoint() -> None:
    with pytest.raises(RuntimeError):
        run_backend_loop(object())


def test_window_port_event_polling_and_controls(monkeypatch: pytest.MonkeyPatch) -> None:
    glfw = _FakeGlfw()
    _install_fake_rendercanvas_glfw(monkeypatch, glfw)
    canvas = _Canvas()
    window = RenderCanvasWindow(canvas=canvas)

    surface = window.create_surface()
    assert surface.backend == "rendercanvas.glfw"

    window.set_windowed(800, 600)
    window.set_fullscreen()
    window.set_maximized()
    window.set_title("X")
    window.close()

    assert canvas.set_size_calls == [(800, 600)]
    assert canvas.titles == ["X"]
    assert canvas.closed == 1

    canvas.emit("resize", size=(640.0, 480.0), pixel_ratio=1.5)
    canvas.emit("focus", focused=True)
    canvas.emit("minimize", minimized=False)
    canvas.emit("close")
    events = window.poll_events()
    assert isinstance(events[0], WindowResizeEvent)
    assert events[0].physical_width == 960
    assert isinstance(events[1], WindowFocusEvent)
    assert isinstance(events[2], WindowMinimizeEvent)
    assert isinstance(events[3], WindowCloseEvent)
    assert window.poll_events() == ()

    canvas.emit("pointer_down", x=1.0, y=2.0, button=1)
    canvas.emit("key_down", key="A")
    canvas.emit("wheel", x=1.0, y=2.0, dy=0.5)
    input_events = window.poll_input_events()
    assert isinstance(input_events[0], PointerEvent)
    assert isinstance(input_events[1], KeyEvent)
    assert isinstance(input_events[2], WheelEvent)
    assert window.poll_input_events() == ()
    assert canvas.request_draw_calls > 0


def test_window_port_accepts_resize_width_height_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    glfw = _FakeGlfw()
    _install_fake_rendercanvas_glfw(monkeypatch, glfw)
    canvas = _Canvas()
    window = RenderCanvasWindow(canvas=canvas)

    canvas.emit("resize", width=800.0, height=600.0, pixel_ratio=1.25)
    events = window.poll_events()

    assert len(events) == 1
    assert isinstance(events[0], WindowResizeEvent)
    assert events[0].logical_width == 800.0
    assert events[0].logical_height == 600.0
    assert events[0].physical_width == 1000
    assert events[0].physical_height == 750


def test_window_port_coalesces_resize_bursts_and_exposes_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    glfw = _FakeGlfw()
    _install_fake_rendercanvas_glfw(monkeypatch, glfw)
    monkeypatch.setenv("ENGINE_WINDOW_RESIZE_REDRAW_MIN_INTERVAL_MS", "1000")
    canvas = _Canvas()
    window = RenderCanvasWindow(canvas=canvas)

    canvas.emit("resize", size=(640.0, 480.0), pixel_ratio=1.0)
    canvas.emit("resize", size=(800.0, 600.0), pixel_ratio=1.0)
    canvas.emit("resize", size=(1024.0, 768.0), pixel_ratio=1.0)

    events = window.poll_events()
    assert len(events) == 1
    assert isinstance(events[0], WindowResizeEvent)
    assert events[0].logical_width == 1024.0
    assert events[0].logical_height == 768.0
    telemetry = window.consume_resize_telemetry()
    assert telemetry["resize_received_total"] == 3
    assert telemetry["resize_emitted_total"] == 1
    assert telemetry["resize_coalesced_total"] == 2
    assert telemetry["resize_redraw_requested_total"] == 1
    assert telemetry["resize_redraw_skipped_total"] >= 1


def test_window_port_accepts_object_style_input_events(monkeypatch: pytest.MonkeyPatch) -> None:
    glfw = _FakeGlfw()
    _install_fake_rendercanvas_glfw(monkeypatch, glfw)
    canvas = _Canvas()
    window = RenderCanvasWindow(canvas=canvas)

    canvas.emit_obj("pointer_down", x=10.0, y=20.0, button=1)
    canvas.emit_obj("key_down", key="Enter")
    canvas.emit_obj("wheel", x=10.0, y=20.0, dy=-1.0)

    input_events = window.poll_input_events()
    assert isinstance(input_events[0], PointerEvent)
    assert isinstance(input_events[1], KeyEvent)
    assert isinstance(input_events[2], WheelEvent)


def test_window_port_accepts_mouse_alias_pointer_events(monkeypatch: pytest.MonkeyPatch) -> None:
    glfw = _FakeGlfw()
    _install_fake_rendercanvas_glfw(monkeypatch, glfw)
    canvas = _Canvas()
    window = RenderCanvasWindow(canvas=canvas)

    canvas.emit("mouse_down", x=10.0, y=20.0, button=1)
    canvas.emit("mouse_move", x=11.0, y=21.0, button=1)
    canvas.emit("mouse_up", x=12.0, y=22.0, button=1)

    input_events = window.poll_input_events()
    assert len(input_events) == 3
    assert all(isinstance(item, PointerEvent) for item in input_events)


def test_window_port_keeps_binding_after_invalid_event_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    glfw = _FakeGlfw()
    _install_fake_rendercanvas_glfw(monkeypatch, glfw)
    canvas = _StrictCanvas()
    window = RenderCanvasWindow(canvas=canvas)

    canvas.emit("pointer_down", x=10.0, y=20.0, button=1)
    canvas.emit("key_down", key="A")

    input_events = window.poll_input_events()
    assert len(input_events) == 2
    assert isinstance(input_events[0], PointerEvent)
    assert isinstance(input_events[1], KeyEvent)


def test_create_rendercanvas_window_factory() -> None:
    canvas = _Canvas()
    window = create_rendercanvas_window(canvas)
    assert isinstance(window, RenderCanvasWindow)
    assert window.canvas is canvas

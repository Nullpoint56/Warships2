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

    def add_event_handler(self, handler, event_type: str) -> None:
        self.handlers.setdefault(event_type, []).append(handler)

    def set_logical_size(self, width: int, height: int) -> None:
        self.set_size_calls.append((width, height))

    def set_title(self, title: str) -> None:
        self.titles.append(title)

    def close(self) -> None:
        self.closed += 1

    def emit(self, event_type: str, **payload) -> None:
        event = {"event_type": event_type, **payload}
        for handler in self.handlers.get(event_type, []):
            handler(event)


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


def test_create_rendercanvas_window_factory() -> None:
    canvas = _Canvas()
    window = create_rendercanvas_window(canvas)
    assert isinstance(window, RenderCanvasWindow)
    assert window.canvas is canvas

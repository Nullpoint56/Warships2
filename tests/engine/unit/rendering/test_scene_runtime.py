from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from engine.rendering.scene_runtime import (
    apply_startup_window_mode,
    get_canvas_logical_size,
    resolve_preserve_aspect,
    resolve_window_mode,
    run_backend_loop,
    stop_backend_loop,
)


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
    def __init__(self, value) -> None:
        self._value = value

    def get_logical_size(self):
        return self._value


class _FakeGlfw:
    FALSE = 0
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


def test_resolve_env_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENGINE_UI_ASPECT_MODE", "contain")
    assert resolve_preserve_aspect()
    monkeypatch.setenv("ENGINE_UI_ASPECT_MODE", "stretch")
    assert not resolve_preserve_aspect()

    monkeypatch.setenv("ENGINE_WINDOW_MODE", "FULLSCREEN")
    assert resolve_window_mode() == "fullscreen"


def test_get_canvas_logical_size_tolerant_parsing() -> None:
    assert get_canvas_logical_size(_Canvas((100, 200))) == (100.0, 200.0)
    assert get_canvas_logical_size(_Canvas(["a", 2])) is None
    assert get_canvas_logical_size(object()) is None


def test_run_backend_loop_prefers_loop_then_run() -> None:
    with_loop = _AutoWithLoop()
    run_backend_loop(with_loop)
    assert with_loop.loop.ran == 1

    with_run = _AutoWithRun()
    run_backend_loop(with_run)
    assert with_run.ran == 1


def test_run_backend_loop_raises_when_no_entrypoint() -> None:
    with pytest.raises(RuntimeError):
        run_backend_loop(object())


def test_stop_backend_loop_stops_when_available() -> None:
    with_loop = _AutoWithLoop()
    stop_backend_loop(with_loop)
    assert with_loop.loop.stopped == 1
    stop_backend_loop(object())


def test_apply_startup_window_mode_maximized(monkeypatch: pytest.MonkeyPatch) -> None:
    glfw = _FakeGlfw()
    _install_fake_rendercanvas_glfw(monkeypatch, glfw)
    apply_startup_window_mode(SimpleNamespace(_window=object()), "maximized")
    assert "set_window_attrib" in glfw.calls
    assert "maximize_window" in glfw.calls


def test_apply_startup_window_mode_fullscreen(monkeypatch: pytest.MonkeyPatch) -> None:
    glfw = _FakeGlfw()
    _install_fake_rendercanvas_glfw(monkeypatch, glfw)
    apply_startup_window_mode(SimpleNamespace(_window=object()), "fullscreen")
    assert "set_window_monitor" in glfw.calls


def test_apply_startup_window_mode_fallback_maximize_when_no_monitor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    glfw = _FakeGlfw()
    glfw.monitor = None
    _install_fake_rendercanvas_glfw(monkeypatch, glfw)
    apply_startup_window_mode(SimpleNamespace(_window=object()), "borderless")
    assert "maximize_window" in glfw.calls

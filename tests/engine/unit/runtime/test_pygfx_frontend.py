from __future__ import annotations

from types import SimpleNamespace

import engine.runtime.pygfx_frontend as frontend_mod


class _RendererWithSize:
    def __init__(self) -> None:
        self.canvas = SimpleNamespace()
        self.canvas_size_calls: list[tuple[int, int]] = []
        self.invalidate_calls = 0
        self.run_callback = None
        self.closed = False

        def _set_size(w: int, h: int) -> None:
            self.canvas_size_calls.append((w, h))

        self.canvas.set_logical_size = _set_size

    def invalidate(self) -> None:
        self.invalidate_calls += 1

    def run(self, callback) -> None:
        self.run_callback = callback

    def close(self) -> None:
        self.closed = True


class _RendererWithoutSize(_RendererWithSize):
    def __init__(self) -> None:
        super().__init__()
        delattr(self.canvas, "set_logical_size")


class _Input:
    def __init__(self, pointer=None, key=None, wheel=None) -> None:
        self._pointer = pointer or []
        self._key = key or []
        self._wheel = wheel or []

    def drain_pointer_events(self):
        return list(self._pointer)

    def drain_key_events(self):
        return list(self._key)

    def drain_wheel_events(self):
        return list(self._wheel)


class _Host:
    def __init__(self, close_after_frame: bool = False) -> None:
        self.close_after_frame = close_after_frame
        self.frame_calls = 0
        self.closed = False

    def handle_pointer_event(self, event) -> bool:
        return bool(event)

    def handle_key_event(self, event) -> bool:
        return bool(event)

    def handle_wheel_event(self, event) -> bool:
        return bool(event)

    def frame(self) -> None:
        self.frame_calls += 1
        if self.close_after_frame:
            self.closed = True

    def is_closed(self) -> bool:
        return self.closed


def test_show_windowed_sets_size_when_supported() -> None:
    renderer = _RendererWithSize()
    window = frontend_mod.PygfxFrontendWindow(
        renderer=renderer, input_controller=_Input(), host=_Host()
    )
    window.show_windowed(800, 600)
    assert renderer.canvas_size_calls == [(800, 600)]


def test_show_windowed_noop_without_setter() -> None:
    renderer = _RendererWithoutSize()
    window = frontend_mod.PygfxFrontendWindow(
        renderer=renderer, input_controller=_Input(), host=_Host()
    )
    window.show_windowed(800, 600)
    assert renderer.canvas_size_calls == []


def test_show_fullscreen_and_maximized_delegate_to_runtime(monkeypatch) -> None:
    calls: list[str] = []

    def _apply(canvas, mode: str) -> None:
        _ = canvas
        calls.append(mode)

    monkeypatch.setattr(frontend_mod, "apply_startup_window_mode", _apply)
    renderer = _RendererWithSize()
    window = frontend_mod.PygfxFrontendWindow(
        renderer=renderer, input_controller=_Input(), host=_Host()
    )
    window.show_fullscreen()
    window.show_maximized()
    assert calls == ["fullscreen", "maximized"]


def test_draw_frame_closes_renderer_when_host_closed() -> None:
    renderer = _RendererWithSize()
    host = _Host(close_after_frame=True)
    window = frontend_mod.PygfxFrontendWindow(
        renderer=renderer,
        input_controller=_Input(pointer=[object()]),
        host=host,
    )
    window._draw_frame()
    assert host.frame_calls == 1
    assert renderer.closed
    assert renderer.invalidate_calls == 1


def test_drain_input_events_without_changes_does_not_invalidate() -> None:
    renderer = _RendererWithSize()
    window = frontend_mod.PygfxFrontendWindow(
        renderer=renderer,
        input_controller=_Input(pointer=[None], key=[None], wheel=[None]),
        host=_Host(close_after_frame=False),
    )
    window._drain_input_events()
    assert renderer.invalidate_calls == 0

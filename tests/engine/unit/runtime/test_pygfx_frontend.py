from __future__ import annotations

from types import SimpleNamespace

from engine.api.input_snapshot import InputSnapshot
import engine.runtime.pygfx_frontend as frontend_mod


class _Renderer:
    def __init__(self) -> None:
        self.canvas = SimpleNamespace()
        self.invalidate_calls = 0
        self.run_callback = None
        self.closed = False
        self.frame_reasons: list[str] = []

    def invalidate(self) -> None:
        self.invalidate_calls += 1

    def run(self, callback) -> None:
        self.run_callback = callback

    def close(self) -> None:
        self.closed = True

    def note_frame_reason(self, reason: str) -> None:
        self.frame_reasons.append(reason)


class _Window:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[int, int] | tuple[()]]] = []
        self.input_events = ()

    def set_fullscreen(self) -> None:
        self.calls.append(("set_fullscreen", ()))

    def set_maximized(self) -> None:
        self.calls.append(("set_maximized", ()))

    def set_windowed(self, width: int, height: int) -> None:
        self.calls.append(("set_windowed", (width, height)))

    def run_loop(self) -> None:
        self.calls.append(("run_loop", ()))

    def stop_loop(self) -> None:
        self.calls.append(("stop_loop", ()))

    def close(self) -> None:
        self.calls.append(("close", ()))

    def poll_input_events(self):
        return self.input_events


class _Input:
    def __init__(self, pointer=None, key=None, wheel=None) -> None:
        self._pointer = pointer or []
        self._key = key or []
        self._wheel = wheel or []

    def build_input_snapshot(self, *, frame_index: int) -> InputSnapshot:
        return InputSnapshot(
            frame_index=frame_index,
            pointer_events=tuple(self._pointer),
            key_events=tuple(self._key),
            wheel_events=tuple(self._wheel),
        )

    def consume_window_input_events(self, events) -> None:
        _ = events


class _Host:
    def __init__(self, close_after_frame: bool = False) -> None:
        self.close_after_frame = close_after_frame
        self.frame_calls = 0
        self.closed = False

    def current_frame_index(self) -> int:
        return 0

    def handle_input_snapshot(self, snapshot: InputSnapshot) -> bool:
        return bool(snapshot.pointer_events or snapshot.key_events or snapshot.wheel_events)

    def frame(self) -> None:
        self.frame_calls += 1
        if self.close_after_frame:
            self.closed = True

    def is_closed(self) -> bool:
        return self.closed


def test_show_windowed_delegates_to_window_port() -> None:
    renderer = _Renderer()
    window_port = _Window()
    window = frontend_mod.PygfxFrontendWindow(
        renderer=renderer,
        window=window_port,
        input_controller=_Input(),
        host=_Host(),
    )
    window.show_windowed(800, 600)
    assert window_port.calls == [("set_windowed", (800, 600))]


def test_show_fullscreen_and_maximized_delegate_to_window_port() -> None:
    renderer = _Renderer()
    window_port = _Window()
    window = frontend_mod.PygfxFrontendWindow(
        renderer=renderer,
        window=window_port,
        input_controller=_Input(),
        host=_Host(),
    )
    window.show_fullscreen()
    window.show_maximized()
    assert window_port.calls == [("set_fullscreen", ()), ("set_maximized", ())]


def test_draw_frame_closes_renderer_when_host_closed() -> None:
    renderer = _Renderer()
    host = _Host(close_after_frame=True)
    window_port = _Window()
    window = frontend_mod.PygfxFrontendWindow(
        renderer=renderer,
        window=window_port,
        input_controller=_Input(pointer=[object()]),
        host=host,
    )
    window._draw_frame()
    assert host.frame_calls == 1
    assert renderer.closed
    assert renderer.invalidate_calls == 1
    assert ("close", ()) in window_port.calls


def test_dispatch_input_snapshot_without_changes_does_not_invalidate() -> None:
    renderer = _Renderer()
    window = frontend_mod.PygfxFrontendWindow(
        renderer=renderer,
        window=_Window(),
        input_controller=_Input(pointer=[], key=[], wheel=[]),
        host=_Host(close_after_frame=False),
    )
    window._dispatch_input_snapshot(window._build_input_snapshot())
    assert renderer.invalidate_calls == 0


def test_dispatch_input_snapshot_records_pointer_event_type_reasons() -> None:
    renderer = _Renderer()
    pointer_event = SimpleNamespace(event_type="pointer_move")
    window = frontend_mod.PygfxFrontendWindow(
        renderer=renderer,
        window=_Window(),
        input_controller=_Input(pointer=[pointer_event]),
        host=_Host(close_after_frame=False),
    )
    window._dispatch_input_snapshot(window._build_input_snapshot())
    assert "input:pointer:pointer_move" in renderer.frame_reasons


def test_run_starts_renderer_then_window_loop() -> None:
    renderer = _Renderer()
    window_port = _Window()
    window = frontend_mod.PygfxFrontendWindow(
        renderer=renderer,
        window=window_port,
        input_controller=_Input(),
        host=_Host(),
    )
    window.run()
    assert renderer.run_callback is not None
    assert window_port.calls[-1] == ("run_loop", ())

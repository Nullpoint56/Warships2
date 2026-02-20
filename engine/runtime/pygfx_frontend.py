"""Engine runtime bootstrap for pygfx frontend."""

from __future__ import annotations

from engine.api.input_snapshot import InputSnapshot
from engine.api.window import WindowPort
from engine.input.input_controller import InputController
from engine.rendering.scene import SceneRenderer
from engine.runtime.host import EngineHost


class PygfxFrontendWindow:
    """Frontend adapter over the pygfx canvas/runtime."""

    def __init__(
        self,
        renderer: SceneRenderer,
        window: WindowPort,
        input_controller: InputController,
        host: EngineHost,
    ) -> None:
        self._renderer = renderer
        self._window = window
        self._input = input_controller
        self._host = host

    def show_fullscreen(self) -> None:
        self._window.set_fullscreen()

    def show_maximized(self) -> None:
        self._window.set_maximized()

    def show_windowed(self, width: int, height: int) -> None:
        self._window.set_windowed(width, height)

    def sync_ui(self) -> None:
        self._renderer.invalidate()

    def run(self) -> None:
        self._renderer.run(self._draw_frame)
        self._window.run_loop()

    def _draw_frame(self) -> None:
        self._renderer.note_frame_reason("draw")
        snapshot = self._build_input_snapshot()
        self._dispatch_input_snapshot(snapshot)
        self._host.frame()
        if self._host.is_closed():
            self._renderer.close()
            self._window.close()

    def _build_input_snapshot(self) -> InputSnapshot:
        window_raw_input = self._window.poll_input_events()
        if window_raw_input:
            self._input.consume_window_input_events(window_raw_input)
        return self._input.build_input_snapshot(frame_index=self._host.current_frame_index())

    def _dispatch_input_snapshot(self, snapshot: InputSnapshot) -> None:
        changed = self._host.handle_input_snapshot(snapshot)
        if snapshot.pointer_events:
            self._renderer.note_frame_reason("input:pointer")
        if snapshot.key_events:
            self._renderer.note_frame_reason("input:key")
        if snapshot.wheel_events:
            self._renderer.note_frame_reason("input:wheel")
        for pointer_event in snapshot.pointer_events:
            event_type = getattr(pointer_event, "event_type", "")
            if isinstance(event_type, str) and event_type.strip():
                normalized_type = event_type.strip().lower().replace(" ", "_")
                self._renderer.note_frame_reason(f"input:pointer:{normalized_type}")
        if changed:
            self._renderer.note_frame_reason("input:changed")
            self._renderer.invalidate()


def create_pygfx_window(
    *,
    renderer: SceneRenderer,
    window: WindowPort,
    input_controller: InputController,
    host: EngineHost,
) -> PygfxFrontendWindow:
    """Build pygfx frontend window from precomposed engine host/runtime services."""
    return PygfxFrontendWindow(
        renderer=renderer,
        window=window,
        input_controller=input_controller,
        host=host,
    )

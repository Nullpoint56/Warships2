"""Engine runtime bootstrap for pygfx frontend."""

from __future__ import annotations

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
        self._drain_input_events()
        self._host.frame()
        if self._host.is_closed():
            self._renderer.close()
            self._window.close()

    def _drain_input_events(self) -> None:
        changed = False
        pointer_count = 0
        for pointer_event in self._input.drain_pointer_events():
            pointer_count += 1
            event_type = getattr(pointer_event, "event_type", "")
            if isinstance(event_type, str) and event_type.strip():
                normalized_type = event_type.strip().lower().replace(" ", "_")
                self._renderer.note_frame_reason(f"input:pointer:{normalized_type}")
            changed = self._host.handle_pointer_event(pointer_event) or changed
        key_count = 0
        for key_event in self._input.drain_key_events():
            key_count += 1
            changed = self._host.handle_key_event(key_event) or changed
        wheel_count = 0
        for wheel_event in self._input.drain_wheel_events():
            wheel_count += 1
            changed = self._host.handle_wheel_event(wheel_event) or changed
        if pointer_count:
            self._renderer.note_frame_reason("input:pointer")
        if key_count:
            self._renderer.note_frame_reason("input:key")
        if wheel_count:
            self._renderer.note_frame_reason("input:wheel")
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

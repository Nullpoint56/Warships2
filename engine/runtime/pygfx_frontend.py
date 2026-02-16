"""Engine runtime bootstrap for pygfx frontend."""

from __future__ import annotations

from engine.input.input_controller import InputController
from engine.rendering.scene import SceneRenderer
from engine.rendering.scene_runtime import apply_startup_window_mode
from engine.runtime.host import EngineHost


class PygfxFrontendWindow:
    """Frontend adapter over the pygfx canvas/runtime."""

    def __init__(
        self,
        renderer: SceneRenderer,
        input_controller: InputController,
        host: EngineHost,
    ) -> None:
        self._renderer = renderer
        self._input = input_controller
        self._host = host

    def show_fullscreen(self) -> None:
        apply_startup_window_mode(self._renderer.canvas, "fullscreen")

    def show_maximized(self) -> None:
        apply_startup_window_mode(self._renderer.canvas, "maximized")

    def show_windowed(self, width: int, height: int) -> None:
        set_size = getattr(self._renderer.canvas, "set_logical_size", None)
        if callable(set_size):
            set_size(width, height)

    def sync_ui(self) -> None:
        self._renderer.invalidate()

    def run(self) -> None:
        self._renderer.run(self._draw_frame)

    def _draw_frame(self) -> None:
        self._drain_input_events()
        self._host.frame()
        if self._host.is_closed():
            self._renderer.close()

    def _drain_input_events(self) -> None:
        changed = False
        for event in self._input.drain_pointer_events():
            changed = self._host.handle_pointer_event(event) or changed
        for event in self._input.drain_key_events():
            changed = self._host.handle_key_event(event) or changed
        for event in self._input.drain_wheel_events():
            changed = self._host.handle_wheel_event(event) or changed
        if changed:
            self._renderer.invalidate()


def create_pygfx_window(
    *,
    renderer: SceneRenderer,
    input_controller: InputController,
    host: EngineHost,
) -> PygfxFrontendWindow:
    """Build pygfx frontend window from precomposed engine host/runtime services."""
    return PygfxFrontendWindow(renderer=renderer, input_controller=input_controller, host=host)



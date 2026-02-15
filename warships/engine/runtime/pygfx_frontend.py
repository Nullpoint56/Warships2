"""Engine runtime bootstrap for pygfx frontend."""

from __future__ import annotations

import os

from warships.app.controller import GameController
from warships.app.engine_adapter import WarshipsAppAdapter
from warships.app.frontend import FrontendBundle, FrontendWindow
from warships.engine.runtime.framework_engine import EngineUIFramework
from warships.ui.board_view import BoardLayout
from warships.ui.game_view import GameView
from warships.ui.input_controller import InputController
from warships.ui.scene import SceneRenderer


class PygfxFrontendWindow(FrontendWindow):
    """Frontend adapter over the pygfx canvas/runtime."""

    def __init__(self, controller: GameController) -> None:
        self._controller = controller
        self._layout = BoardLayout()
        self._renderer = SceneRenderer()
        self._view = GameView(self._renderer, self._layout)
        self._app = WarshipsAppAdapter(controller)
        self._framework = EngineUIFramework(app=self._app, renderer=self._renderer, layout=self._layout)
        self._input = InputController(on_click_queued=self._renderer.invalidate)
        self._input.bind(self._renderer.canvas)
        self._debug_ui = os.getenv("WARSHIPS_DEBUG_UI", "0") == "1"
        self._debug_labels_state: list[str] = []

    def show_fullscreen(self) -> None:
        return

    def show_maximized(self) -> None:
        return

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
        self._framework.sync_ui_state()
        ui = self._controller.ui_state()
        self._debug_labels_state = self._view.render(ui, self._debug_ui, self._debug_labels_state)
        if ui.is_closing:
            self._renderer.close()

    def _drain_input_events(self) -> None:
        changed = False
        for event in self._input.drain_pointer_events():
            changed = self._framework.handle_pointer_event(event) or changed
        for event in self._input.drain_key_events():
            changed = self._framework.handle_key_event(event) or changed
        for event in self._input.drain_wheel_events():
            changed = self._framework.handle_wheel_event(event) or changed
        if changed:
            self._renderer.invalidate()


def create_pygfx_frontend(controller: GameController) -> FrontendBundle:
    """Build pygfx adapter and event-loop runner."""
    window = PygfxFrontendWindow(controller)
    return FrontendBundle(window=window, run_event_loop=window.run)


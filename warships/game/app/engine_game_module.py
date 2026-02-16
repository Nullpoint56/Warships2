"""Warships GameModule adapter for engine-hosted runtime."""

from __future__ import annotations

from engine.api.game_module import GameModule, HostControl, HostFrameContext
from engine.input.input_controller import KeyEvent, PointerEvent, WheelEvent
from engine.runtime.framework_engine import EngineUIFramework
from warships.game.app.controller import GameController
from warships.game.ui.game_view import GameView


class WarshipsGameModule(GameModule):
    """Engine-facing adapter that delegates to existing Warships app graph."""

    def __init__(
        self,
        controller: GameController,
        framework: EngineUIFramework,
        view: GameView,
        debug_ui: bool,
    ) -> None:
        self._controller = controller
        self._framework = framework
        self._view = view
        self._debug_ui = debug_ui
        self._debug_labels_state: list[str] = []
        self._host: HostControl | None = None

    def on_start(self, host: HostControl) -> None:
        self._host = host

    def on_pointer_event(self, event: PointerEvent) -> bool:
        return self._framework.handle_pointer_event(event)

    def on_key_event(self, event: KeyEvent) -> bool:
        return self._framework.handle_key_event(event)

    def on_wheel_event(self, event: WheelEvent) -> bool:
        return self._framework.handle_wheel_event(event)

    def on_frame(self, context: HostFrameContext) -> None:
        _ = context
        self._framework.sync_ui_state()
        ui = self._controller.ui_state()
        self._debug_labels_state = self._view.render(ui, self._debug_ui, self._debug_labels_state)
        if ui.is_closing and self._host is not None:
            self._host.close()

    def should_close(self) -> bool:
        return self._controller.ui_state().is_closing

    def on_shutdown(self) -> None:
        return

"""Warships GameModule adapter for engine-hosted runtime."""

from __future__ import annotations

from dataclasses import dataclass

from engine.api.events import Subscription, create_event_bus
from engine.api.game_module import GameModule, HostControl, HostFrameContext
from engine.input.input_controller import KeyEvent, PointerEvent, WheelEvent
from engine.runtime.framework_engine import EngineUIFramework
from warships.game.app.controller import GameController
from warships.game.ui.game_view import GameView


@dataclass(frozen=True, slots=True)
class _CloseRequested:
    """Internal runtime event used to decouple close signaling."""


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
        self._events = create_event_bus()
        self._close_subscription: Subscription | None = None
        self._close_task_id: int | None = None

    def on_start(self, host: HostControl) -> None:
        self._host = host
        self._close_subscription = self._events.subscribe(_CloseRequested, self._on_close_requested)

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
        if ui.is_closing:
            self._schedule_close_request()

    def should_close(self) -> bool:
        return False

    def on_shutdown(self) -> None:
        if self._host is not None and self._close_task_id is not None:
            self._host.cancel_task(self._close_task_id)
            self._close_task_id = None
        if self._close_subscription is not None:
            self._events.unsubscribe(self._close_subscription)
            self._close_subscription = None
        return

    def _schedule_close_request(self) -> None:
        if self._host is None or self._close_task_id is not None:
            return
        self._close_task_id = self._host.call_later(0.0, self._emit_close_requested)

    def _emit_close_requested(self) -> None:
        self._close_task_id = None
        self._events.publish(_CloseRequested())

    def _on_close_requested(self, _event: _CloseRequested) -> None:
        if self._host is None:
            return
        self._host.close()

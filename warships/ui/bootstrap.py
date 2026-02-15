"""pygfx frontend bootstrap and runtime wiring."""

from __future__ import annotations

import os

from warships.app.controller import GameController
from warships.app.events import BoardCellPressed, ButtonPressed, CharTyped, KeyPressed, PointerMoved, PointerReleased
from warships.app.frontend import FrontendBundle, FrontendWindow
from warships.ui.board_view import BoardLayout
from warships.ui.framework import (
    ModalInputState,
    build_modal_text_input_widget,
    build_interaction_plan,
    can_scroll_with_wheel,
    map_key_name,
    route_non_modal_key_event,
    route_modal_key_event,
    route_modal_pointer_event,
    resolve_pointer_button,
)
from warships.ui.game_view import GameView
from warships.ui.input_controller import InputController, KeyEvent, PointerEvent, WheelEvent
from warships.ui.scene import SceneRenderer


class PygfxFrontendWindow(FrontendWindow):
    """Frontend adapter over the pygfx canvas/runtime."""

    def __init__(self, controller: GameController) -> None:
        self._controller = controller
        self._layout = BoardLayout()
        self._renderer = SceneRenderer()
        self._view = GameView(self._renderer, self._layout)
        self._input = InputController(on_click_queued=self._renderer.invalidate)
        self._input.bind(self._renderer.canvas)
        self._debug_ui = os.getenv("WARSHIPS_DEBUG_UI", "0") == "1"
        self._debug_labels_state: list[str] = []
        self._requested_size: tuple[int, int] | None = None
        self._modal_state = ModalInputState()

    def show_fullscreen(self) -> None:
        # SceneRenderer applies startup window mode via env + backend.
        return

    def show_maximized(self) -> None:
        return

    def show_windowed(self, width: int, height: int) -> None:
        self._requested_size = (width, height)
        set_size = getattr(self._renderer.canvas, "set_logical_size", None)
        if callable(set_size):
            set_size(width, height)

    def sync_ui(self) -> None:
        self._renderer.invalidate()

    def run(self) -> None:
        self._renderer.run(self._draw_frame)

    def _draw_frame(self) -> None:
        self._drain_input_events()
        ui = self._controller.ui_state()
        modal = build_modal_text_input_widget(ui)
        self._modal_state.sync(modal)
        self._debug_labels_state = self._view.render(ui, self._debug_ui, self._debug_labels_state)
        if ui.is_closing:
            self._renderer.close()

    def _drain_input_events(self) -> None:
        changed = False
        for event in self._input.drain_pointer_events():
            changed = self._handle_pointer_event(event) or changed
        for event in self._input.drain_key_events():
            changed = self._handle_key_event(event) or changed
        for event in self._input.drain_wheel_events():
            changed = self._handle_wheel_event(event) or changed
        if changed:
            self._renderer.invalidate()

    def _handle_pointer_event(self, event: PointerEvent) -> bool:
        x, y = self._renderer.to_design_space(event.x, event.y)
        if event.event_type == "pointer_move":
            return self._controller.handle_pointer_move(PointerMoved(x=x, y=y))
        if event.event_type == "pointer_up":
            return self._controller.handle_pointer_release(PointerReleased(x=x, y=y, button=event.button))
        if event.event_type != "pointer_down":
            return False

        ui = self._controller.ui_state()
        modal = build_modal_text_input_widget(ui)
        if modal is not None:
            route = route_modal_pointer_event(modal, self._modal_state, x, y, event.button)
            if route.focus_input is not None:
                self._modal_state.input_focused = route.focus_input
            if route.button_id is not None:
                return self._controller.handle_button(ButtonPressed(route.button_id))
            return False

        interactions = build_interaction_plan(ui)
        if event.button == 1:
            button_id = resolve_pointer_button(interactions, x, y)
            if button_id is not None:
                return self._controller.handle_button(ButtonPressed(button_id))
            if interactions.allows_ai_board_click:
                ai_cell = self._layout.screen_to_cell(True, x, y)
                if ai_cell is not None:
                    return self._controller.handle_board_click(BoardCellPressed(True, ai_cell))
        return self._controller.handle_pointer_down(x, y, event.button)

    def _handle_key_event(self, event: KeyEvent) -> bool:
        ui = self._controller.ui_state()
        modal = build_modal_text_input_widget(ui)
        if modal is not None:
            mapped = map_key_name(event.value) if event.event_type == "key_down" else None
            route = route_modal_key_event(event.event_type, event.value, mapped, self._modal_state)
            if route.char is not None:
                return self._controller.handle_char_typed(CharTyped(route.char))
            if route.key is not None:
                return self._controller.handle_key_pressed(KeyPressed(route.key))
            return False

        interactions = build_interaction_plan(ui)
        route = route_non_modal_key_event(event.event_type, event.value, interactions)
        if route.controller_char is not None:
            return self._controller.handle_char_typed(CharTyped(route.controller_char))
        if route.controller_key is None:
            return False
        if self._controller.handle_key_pressed(KeyPressed(route.controller_key)):
            return True
        shortcut_button = route.shortcut_button_id
        if shortcut_button is None:
            return False
        return self._controller.handle_button(ButtonPressed(shortcut_button))

    def _handle_wheel_event(self, event: WheelEvent) -> bool:
        x, y = self._renderer.to_design_space(event.x, event.y)
        ui = self._controller.ui_state()
        interactions = build_interaction_plan(ui)
        if not can_scroll_with_wheel(interactions, x, y):
            return False
        return self._controller.handle_wheel(x, y, event.dy)
def create_pygfx_frontend(controller: GameController) -> FrontendBundle:
    """Build pygfx adapter and event-loop runner."""
    window = PygfxFrontendWindow(controller)
    return FrontendBundle(window=window, run_event_loop=window.run)

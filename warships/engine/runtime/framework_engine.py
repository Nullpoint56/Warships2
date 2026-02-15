"""Engine runtime UI framework routing."""

from __future__ import annotations

from warships.core.models import Coord
from warships.engine.api.app_port import EngineAppPort
from warships.engine.api.render import RenderAPI
from warships.ui.board_view import BoardLayout
from warships.ui.framework.interactions import build_interaction_plan, can_scroll_with_wheel, resolve_pointer_button
from warships.ui.framework.key_routing import map_key_name, route_non_modal_key_event
from warships.ui.framework.modal_runtime import ModalInputState, route_modal_key_event, route_modal_pointer_event
from warships.ui.framework.widgets import build_modal_text_input_widget
from warships.ui.input_controller import KeyEvent, PointerEvent, WheelEvent


class EngineUIFramework:
    """Coordinates input routing between engine runtime and app port."""

    def __init__(self, app: EngineAppPort, renderer: RenderAPI, layout: BoardLayout) -> None:
        self._app = app
        self._renderer = renderer
        self._layout = layout
        self._modal_state = ModalInputState()

    def sync_ui_state(self) -> None:
        """Sync framework runtime state from app UI snapshot."""
        ui = self._app.ui_state()
        modal = build_modal_text_input_widget(ui)
        self._modal_state.sync(modal)

    def handle_pointer_event(self, event: PointerEvent) -> bool:
        """Route pointer event to app actions."""
        x, y = self._renderer.to_design_space(event.x, event.y)
        if event.event_type == "pointer_move":
            return self._app.on_pointer_move(x=x, y=y)
        if event.event_type == "pointer_up":
            return self._app.on_pointer_release(x=x, y=y, button=event.button)
        if event.event_type != "pointer_down":
            return False

        ui = self._app.ui_state()
        modal = build_modal_text_input_widget(ui)
        if modal is not None:
            route = route_modal_pointer_event(modal, self._modal_state, x, y, event.button)
            if route.focus_input is not None:
                self._modal_state.input_focused = route.focus_input
            if route.button_id is not None:
                return self._app.on_button(route.button_id)
            return False

        interactions = build_interaction_plan(ui)
        if event.button == 1:
            button_id = resolve_pointer_button(interactions, x, y)
            if button_id is not None:
                return self._app.on_button(button_id)
            if interactions.allows_ai_board_click:
                ai_cell = self._layout.screen_to_cell(True, x, y)
                if ai_cell is not None:
                    return self._app.on_board_click(True, Coord(ai_cell.row, ai_cell.col))
        return self._app.on_pointer_down(x=x, y=y, button=event.button)

    def handle_key_event(self, event: KeyEvent) -> bool:
        """Route key/char event to app actions."""
        ui = self._app.ui_state()
        modal = build_modal_text_input_widget(ui)
        if modal is not None:
            mapped = map_key_name(event.value) if event.event_type == "key_down" else None
            route = route_modal_key_event(event.event_type, event.value, mapped, self._modal_state)
            if route.char is not None:
                return self._app.on_char(route.char)
            if route.key is not None:
                return self._app.on_key(route.key)
            return False

        interactions = build_interaction_plan(ui)
        route = route_non_modal_key_event(event.event_type, event.value, interactions)
        if route.controller_char is not None:
            return self._app.on_char(route.controller_char)
        if route.controller_key is None:
            return False
        if self._app.on_key(route.controller_key):
            return True
        if route.shortcut_button_id is None:
            return False
        return self._app.on_button(route.shortcut_button_id)

    def handle_wheel_event(self, event: WheelEvent) -> bool:
        """Route wheel event to app actions."""
        x, y = self._renderer.to_design_space(event.x, event.y)
        ui = self._app.ui_state()
        interactions = build_interaction_plan(ui)
        if not can_scroll_with_wheel(interactions, x, y):
            return False
        return self._app.on_wheel(x=x, y=y, dy=event.dy)


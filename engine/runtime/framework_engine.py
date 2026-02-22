"""Engine runtime UI framework routing."""

from __future__ import annotations

import logging

from engine.api.app_port import EngineAppPort, InteractionPlanView
from engine.api.input_events import KeyEvent, PointerEvent, WheelEvent
from engine.api.input_snapshot import InputSnapshot
from engine.api.render import RenderAPI
from engine.api.ui_primitives import (
    GridLayout,
    ModalInputState,
    can_scroll_with_wheel,
    map_key_name,
    resolve_pointer_button,
    route_modal_key_event,
    route_modal_pointer_event,
    route_non_modal_key_event,
)
from engine.runtime.commands import RuntimeCommandMap
from engine.runtime.config import get_runtime_config
from engine.runtime.ui_space import UISpaceTransform, resolve_ui_space_transform


class EngineUIFramework:
    """Coordinates input routing between engine runtime and app port."""

    def __init__(self, app: EngineAppPort, renderer: RenderAPI, layout: GridLayout) -> None:
        self._app = app
        self._renderer = renderer
        self._layout = layout
        self._ui_transform: UISpaceTransform = resolve_ui_space_transform(
            app=app,
            renderer=renderer,
        )
        self._modal_state = ModalInputState()
        self._trace_input = bool(get_runtime_config().input.trace_enabled)
        self._trace_log = logging.getLogger("engine.inputtrace")

    def sync_ui_state(self) -> None:
        """Sync framework runtime state from app UI snapshot."""
        self._modal_state.sync(self._app.modal_widget())

    def handle_pointer_event(self, event: PointerEvent) -> bool:
        """Route pointer event to app actions."""
        x, y = self._renderer.to_design_space(event.x, event.y)
        app_x, app_y = self._ui_transform.engine_to_app(x, y)
        if self._trace_input:
            self._trace_log.info(
                "pointer_event type=%s raw=(%.2f,%.2f) design=(%.2f,%.2f) app=(%.2f,%.2f) button=%d",
                event.event_type,
                float(event.x),
                float(event.y),
                float(x),
                float(y),
                float(app_x),
                float(app_y),
                int(event.button),
            )
        if event.event_type == "pointer_move":
            return self._app.on_pointer_move(x=app_x, y=app_y)
        if event.event_type == "pointer_up":
            return self._app.on_pointer_release(x=app_x, y=app_y, button=event.button)
        if event.event_type != "pointer_down":
            return False

        modal = self._app.modal_widget()
        if modal is not None:
            route = route_modal_pointer_event(modal, self._modal_state, app_x, app_y, event.button)
            if route.focus_input is not None:
                self._modal_state.input_focused = route.focus_input
            if route.button_id is not None:
                return self._app.on_button(route.button_id)
            return False

        interactions = self._app.interaction_plan()
        if event.button == 1:
            button_id = resolve_pointer_button(interactions, app_x, app_y)
            if self._trace_input:
                self._trace_log.info("pointer_down resolve_button=%s", button_id)
            if button_id is not None:
                return self._app.on_button(button_id)
            if interactions.cell_click_surface is not None:
                grid_cell = self._layout.screen_to_cell(
                    interactions.cell_click_surface,
                    app_x,
                    app_y,
                )
                if self._trace_input:
                    self._trace_log.info(
                        "pointer_down cell_surface=%s cell=%s",
                        interactions.cell_click_surface,
                        grid_cell,
                    )
                if grid_cell is not None:
                    return self._app.on_cell_click(
                        interactions.cell_click_surface, grid_cell.row, grid_cell.col
                    )
        handled = self._app.on_pointer_down(x=app_x, y=app_y, button=event.button)
        if self._trace_input:
            self._trace_log.info("pointer_down fallback_handled=%s", bool(handled))
        return handled

    def handle_key_event(self, event: KeyEvent) -> bool:
        """Route key/char event to app actions."""
        modal = self._app.modal_widget()
        if modal is not None:
            mapped = map_key_name(event.value) if event.event_type == "key_down" else None
            modal_route = route_modal_key_event(
                event.event_type, event.value, mapped, self._modal_state
            )
            if modal_route.char is not None:
                return self._app.on_char(modal_route.char)
            if modal_route.key is not None:
                return self._app.on_key(modal_route.key)
            return False

        interactions = self._app.interaction_plan()
        non_modal_route = route_non_modal_key_event(event.event_type, event.value, interactions)
        if non_modal_route.controller_char is not None:
            return self._app.on_char(non_modal_route.controller_char)
        if non_modal_route.controller_key is None:
            return False
        if self._app.on_key(non_modal_route.controller_key):
            return True
        shortcut_button_id = self._resolve_shortcut_button_command(
            key=non_modal_route.controller_key,
            interactions=interactions,
        )
        if shortcut_button_id is None:
            return False
        return self._app.on_button(shortcut_button_id)

    def handle_wheel_event(self, event: WheelEvent) -> bool:
        """Route wheel event to app actions."""
        x, y = self._renderer.to_design_space(event.x, event.y)
        app_x, app_y = self._ui_transform.engine_to_app(x, y)
        interactions = self._app.interaction_plan()
        if not can_scroll_with_wheel(interactions, app_x, app_y):
            return False
        return self._app.on_wheel(x=app_x, y=app_y, dy=event.dy)

    def handle_input_snapshot(self, snapshot: InputSnapshot) -> bool:
        """Route one immutable input snapshot through framework handlers."""
        changed = False
        if self._trace_input:
            self._trace_log.info(
                "input_snapshot frame=%d ptr_pressed=%s ptr_released=%s key_pressed=%s wheel=%.3f",
                int(snapshot.frame_index),
                sorted(int(button) for button in snapshot.mouse.just_pressed_buttons),
                sorted(int(button) for button in snapshot.mouse.just_released_buttons),
                sorted(str(key) for key in snapshot.keyboard.just_pressed_keys),
                float(snapshot.mouse.wheel_delta),
            )
        mx = float(snapshot.mouse.x)
        my = float(snapshot.mouse.y)
        if snapshot.mouse.delta_x != 0.0 or snapshot.mouse.delta_y != 0.0:
            changed = self.handle_pointer_event(
                PointerEvent("pointer_move", mx, my, 0)
            ) or changed
        for button in sorted(snapshot.mouse.just_pressed_buttons):
            changed = self.handle_pointer_event(
                PointerEvent("pointer_down", mx, my, int(button))
            ) or changed
        for button in sorted(snapshot.mouse.just_released_buttons):
            changed = self.handle_pointer_event(
                PointerEvent("pointer_up", mx, my, int(button))
            ) or changed
        for key in sorted(snapshot.keyboard.just_pressed_keys):
            changed = self.handle_key_event(KeyEvent("key_down", str(key))) or changed
        for char in snapshot.keyboard.text_input:
            changed = self.handle_key_event(KeyEvent("char", str(char))) or changed
        if snapshot.mouse.wheel_delta != 0.0:
            changed = self.handle_wheel_event(WheelEvent(mx, my, float(snapshot.mouse.wheel_delta))) or changed
        return changed

    @staticmethod
    def _resolve_shortcut_button_command(
        *,
        key: str,
        interactions: InteractionPlanView,
    ) -> str | None:
        commands = RuntimeCommandMap()
        for shortcut_key, button_id in interactions.shortcut_buttons.items():
            commands.bind_key_down(shortcut_key, f"button:{button_id}")
        resolved = commands.resolve_key_event("key_down", key)
        if resolved is None or not resolved.name.startswith("button:"):
            return None
        return resolved.name.removeprefix("button:")

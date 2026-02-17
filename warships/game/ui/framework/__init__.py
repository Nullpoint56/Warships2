"""Reusable UI interaction framework primitives."""

from engine.api.ui_primitives import (
    ModalInputState,
    ModalKeyRoute,
    ModalPointerRoute,
    NonModalKeyRoute,
    can_scroll_with_wheel,
    map_key_name,
    resolve_pointer_button,
    route_modal_key_event,
    route_modal_pointer_event,
    route_non_modal_key_event,
)
from warships.game.ui.framework.widgets import (
    ModalTextInputWidget,
    build_modal_text_input_widget,
    render_modal_text_input_widget,
    resolve_modal_pointer_target,
)

__all__ = [
    "ModalInputState",
    "ModalKeyRoute",
    "NonModalKeyRoute",
    "ModalPointerRoute",
    "ModalTextInputWidget",
    "build_modal_text_input_widget",
    "can_scroll_with_wheel",
    "map_key_name",
    "render_modal_text_input_widget",
    "route_non_modal_key_event",
    "route_modal_key_event",
    "route_modal_pointer_event",
    "resolve_modal_pointer_target",
    "resolve_pointer_button",
]

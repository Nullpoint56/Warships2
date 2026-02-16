"""Reusable UI interaction framework primitives."""

from engine.ui_runtime.interactions import (
    NonModalKeyRoute,
    can_scroll_with_wheel,
    resolve_pointer_button,
    route_non_modal_key_event,
)
from engine.ui_runtime.keymap import map_key_name
from engine.ui_runtime.modal_runtime import (
    ModalInputState,
    ModalKeyRoute,
    ModalPointerRoute,
    route_modal_key_event,
    route_modal_pointer_event,
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

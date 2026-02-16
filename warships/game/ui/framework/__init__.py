"""Reusable UI interaction framework primitives."""

from engine.ui_runtime.modal_runtime import ModalInputState
from engine.ui_runtime.modal_runtime import ModalKeyRoute
from engine.ui_runtime.modal_runtime import ModalPointerRoute
from engine.ui_runtime.modal_runtime import route_modal_key_event
from engine.ui_runtime.modal_runtime import route_modal_pointer_event
from engine.ui_runtime.interactions import NonModalKeyRoute
from engine.ui_runtime.interactions import can_scroll_with_wheel
from engine.ui_runtime.interactions import resolve_pointer_button
from engine.ui_runtime.interactions import route_non_modal_key_event
from engine.ui_runtime.keymap import map_key_name
from warships.game.ui.framework.widgets import ModalTextInputWidget
from warships.game.ui.framework.widgets import build_modal_text_input_widget
from warships.game.ui.framework.widgets import render_modal_text_input_widget
from warships.game.ui.framework.widgets import resolve_modal_pointer_target

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

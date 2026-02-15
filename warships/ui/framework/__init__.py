"""Reusable UI interaction framework primitives."""

from warships.ui.framework.interactions import InteractionPlan
from warships.ui.framework.interactions import build_interaction_plan
from warships.ui.framework.interactions import can_scroll_with_wheel
from warships.ui.framework.interactions import resolve_key_shortcut
from warships.ui.framework.interactions import resolve_pointer_button
from warships.engine.ui_runtime.modal_runtime import ModalInputState
from warships.engine.ui_runtime.modal_runtime import ModalKeyRoute
from warships.engine.ui_runtime.modal_runtime import ModalPointerRoute
from warships.engine.ui_runtime.modal_runtime import route_modal_key_event
from warships.engine.ui_runtime.modal_runtime import route_modal_pointer_event
from warships.ui.framework.key_routing import NonModalKeyRoute
from warships.ui.framework.key_routing import map_key_name
from warships.ui.framework.key_routing import route_non_modal_key_event
from warships.ui.framework.widgets import ModalTextInputWidget
from warships.ui.framework.widgets import build_modal_text_input_widget
from warships.ui.framework.widgets import render_modal_text_input_widget
from warships.ui.framework.widgets import resolve_modal_pointer_target

__all__ = [
    "InteractionPlan",
    "ModalInputState",
    "ModalKeyRoute",
    "NonModalKeyRoute",
    "ModalPointerRoute",
    "ModalTextInputWidget",
    "build_interaction_plan",
    "build_modal_text_input_widget",
    "can_scroll_with_wheel",
    "map_key_name",
    "render_modal_text_input_widget",
    "route_non_modal_key_event",
    "route_modal_key_event",
    "route_modal_pointer_event",
    "resolve_modal_pointer_target",
    "resolve_key_shortcut",
    "resolve_pointer_button",
]

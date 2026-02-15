"""Engine-owned UI runtime helpers."""

from warships.engine.ui_runtime.board_layout import BoardLayout, Rect
from warships.engine.ui_runtime.interactions import (
    NonModalKeyRoute,
    can_scroll_with_wheel,
    resolve_pointer_button,
    route_non_modal_key_event,
)
from warships.engine.ui_runtime.keymap import map_key_name
from warships.engine.ui_runtime.modal_runtime import (
    ModalInputState,
    ModalKeyRoute,
    ModalPointerRoute,
    route_modal_key_event,
    route_modal_pointer_event,
)

__all__ = [
    "ModalInputState",
    "ModalKeyRoute",
    "ModalPointerRoute",
    "NonModalKeyRoute",
    "BoardLayout",
    "Rect",
    "can_scroll_with_wheel",
    "map_key_name",
    "resolve_pointer_button",
    "route_non_modal_key_event",
    "route_modal_key_event",
    "route_modal_pointer_event",
]

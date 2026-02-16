"""Engine-owned UI runtime helpers."""

from engine.ui_runtime.geometry import CellCoord, Rect
from engine.ui_runtime.grid_layout import GridLayout
from engine.ui_runtime.interactions import (
    NonModalKeyRoute,
    can_scroll_with_wheel,
    resolve_pointer_button,
    route_non_modal_key_event,
)
from engine.ui_runtime.keymap import map_key_name
from engine.ui_runtime.list_viewport import can_scroll_down as can_scroll_list_down
from engine.ui_runtime.list_viewport import clamp_scroll, visible_slice
from engine.ui_runtime.modal_runtime import (
    ModalInputState,
    ModalKeyRoute,
    ModalPointerRoute,
    route_modal_key_event,
    route_modal_pointer_event,
)
from engine.ui_runtime.prompt_runtime import (
    PromptInteractionOutcome,
    PromptState,
    PromptView,
    close_prompt,
    handle_button as handle_prompt_button,
    handle_char as handle_prompt_char,
    handle_key as handle_prompt_key,
    open_prompt,
    sync_prompt,
)
from engine.ui_runtime.scroll import ScrollOutcome, apply_wheel_scroll
from engine.ui_runtime.widgets import Button

__all__ = [
    "ModalInputState",
    "ModalKeyRoute",
    "ModalPointerRoute",
    "NonModalKeyRoute",
    "Button",
    "CellCoord",
    "GridLayout",
    "PromptInteractionOutcome",
    "PromptState",
    "PromptView",
    "Rect",
    "ScrollOutcome",
    "apply_wheel_scroll",
    "can_scroll_list_down",
    "can_scroll_with_wheel",
    "clamp_scroll",
    "close_prompt",
    "handle_prompt_button",
    "handle_prompt_char",
    "handle_prompt_key",
    "map_key_name",
    "open_prompt",
    "resolve_pointer_button",
    "visible_slice",
    "route_non_modal_key_event",
    "route_modal_key_event",
    "route_modal_pointer_event",
    "sync_prompt",
]

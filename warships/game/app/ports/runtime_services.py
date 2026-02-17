"""App-local runtime service ports that wrap engine mechanisms."""

from engine.api.action_dispatch import (
    ActionDispatcher,
    create_action_dispatcher,
)
from engine.api.ui_primitives import (
    apply_wheel_scroll,
    can_scroll_list_down,
    clamp_scroll,
    close_prompt,
    handle_prompt_button,
    handle_prompt_char,
    handle_prompt_key,
    open_prompt,
    sync_prompt,
    visible_slice,
)

__all__ = [
    "ActionDispatcher",
    "apply_wheel_scroll",
    "can_scroll_list_down",
    "clamp_scroll",
    "close_prompt",
    "handle_prompt_button",
    "handle_prompt_char",
    "handle_prompt_key",
    "create_action_dispatcher",
    "open_prompt",
    "sync_prompt",
    "visible_slice",
]

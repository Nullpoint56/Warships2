"""App-local runtime service ports that wrap engine mechanisms."""

from engine.runtime.action_dispatch import ActionDispatcher
from engine.ui_runtime.list_viewport import can_scroll_down as can_scroll_list_down
from engine.ui_runtime.list_viewport import clamp_scroll, visible_slice
from engine.ui_runtime.prompt_runtime import (
    close_prompt,
    open_prompt,
    sync_prompt,
)
from engine.ui_runtime.prompt_runtime import (
    handle_button as handle_prompt_button,
)
from engine.ui_runtime.prompt_runtime import (
    handle_char as handle_prompt_char,
)
from engine.ui_runtime.prompt_runtime import (
    handle_key as handle_prompt_key,
)
from engine.ui_runtime.scroll import apply_wheel_scroll

__all__ = [
    "ActionDispatcher",
    "apply_wheel_scroll",
    "can_scroll_list_down",
    "clamp_scroll",
    "close_prompt",
    "handle_prompt_button",
    "handle_prompt_char",
    "handle_prompt_key",
    "open_prompt",
    "sync_prompt",
    "visible_slice",
]

"""App-local runtime service ports that wrap engine mechanisms."""

from engine.api.action_dispatch import (
    ActionDispatcher,
    DirectActionHandler,
    PrefixedActionHandler,
)
from engine.api.composition import ActionDispatcherFactory
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


def create_action_dispatcher(
    *,
    direct_handlers: dict[str, DirectActionHandler],
    prefixed_handlers: tuple[tuple[str, PrefixedActionHandler], ...],
    factory: ActionDispatcherFactory,
) -> ActionDispatcher:
    """Create action dispatcher for app command routing using supplied factory."""
    return factory(direct_handlers, prefixed_handlers)


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

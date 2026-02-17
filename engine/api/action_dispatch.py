"""Public action-dispatch API contracts."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

DirectActionHandler = Callable[[], bool]
PrefixedActionHandler = Callable[[str], bool]


class ActionDispatcher(Protocol):
    """Resolve and dispatch action IDs."""

    def dispatch(self, action_id: str) -> bool | None:
        """Dispatch action id. Return None when no handler exists."""


def create_action_dispatcher(
    *,
    direct_handlers: dict[str, DirectActionHandler],
    prefixed_handlers: tuple[tuple[str, PrefixedActionHandler], ...],
) -> ActionDispatcher:
    """Create default dispatcher implementation."""
    from engine.runtime.action_dispatch import RuntimeActionDispatcher

    return RuntimeActionDispatcher(
        direct_handlers=direct_handlers,
        prefixed_handlers=prefixed_handlers,
    )

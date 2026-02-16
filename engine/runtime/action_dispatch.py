"""Generic action-dispatch helpers for runtime/controller orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


DirectActionHandler = Callable[[], bool]
PrefixedActionHandler = Callable[[str], bool]


@dataclass(frozen=True, slots=True)
class ActionDispatcher:
    """Resolve and dispatch action ids by direct match or prefix handlers."""

    direct_handlers: dict[str, DirectActionHandler]
    prefixed_handlers: tuple[tuple[str, PrefixedActionHandler], ...]

    def dispatch(self, action_id: str) -> bool | None:
        """Dispatch action id. Return None when no handler exists."""
        handler = self.direct_handlers.get(action_id)
        if handler is not None:
            return handler()
        for prefix, prefixed_handler in self.prefixed_handlers:
            if action_id.startswith(prefix):
                suffix = action_id.split(":", 1)[1]
                return prefixed_handler(suffix)
        return None

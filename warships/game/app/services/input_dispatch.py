"""Input dispatch helpers for controller button routing."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


DirectButtonHandler = Callable[[], bool]
PrefixedButtonHandler = Callable[[str], bool]


@dataclass(frozen=True, slots=True)
class ButtonDispatcher:
    """Resolve and dispatch button actions by id and optional prefix."""

    direct_handlers: dict[str, DirectButtonHandler]
    prefixed_handlers: tuple[tuple[str, PrefixedButtonHandler], ...]

    def dispatch(self, button_id: str) -> bool | None:
        """Dispatch a button id. Return None when no handler exists."""
        handler = self.direct_handlers.get(button_id)
        if handler is not None:
            return handler()
        for prefix, prefixed_handler in self.prefixed_handlers:
            if button_id.startswith(prefix):
                suffix = button_id.split(":", 1)[1]
                return prefixed_handler(suffix)
        return None

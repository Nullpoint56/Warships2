"""Public action-dispatch API contracts."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

DirectActionHandler = Callable[[], bool]
PrefixedActionHandler = Callable[[str], bool]


@runtime_checkable
class ActionDispatcher(Protocol):
    """Resolve and dispatch action IDs."""

    def dispatch(self, action_id: str) -> bool | None:
        """Dispatch action id. Return None when no handler exists."""

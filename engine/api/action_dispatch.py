"""Public action-dispatch API contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

DirectActionHandler = Callable[[], bool]
PrefixedActionHandler = Callable[[str], bool]


class ActionDispatcher(ABC):
    """Resolve and dispatch action IDs."""

    @abstractmethod
    def dispatch(self, action_id: str) -> bool | None:
        """Dispatch action id. Return None when no handler exists."""

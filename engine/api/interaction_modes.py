"""Public interaction-mode API contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class InteractionMode:
    """Public interaction mode shape."""

    name: str
    allow_pointer: bool = True
    allow_keyboard: bool = True
    allow_wheel: bool = True


@runtime_checkable
class InteractionModeMachine(Protocol):
    """Public interaction mode machine contract."""

    @property
    def current_mode(self) -> str:
        """Return current mode name."""

    def register(self, mode: InteractionMode) -> None:
        """Register/replace mode."""

    def set_mode(self, mode_name: str) -> None:
        """Switch mode."""

    def allows_pointer(self) -> bool:
        """Return whether pointer input is allowed."""

    def allows_keyboard(self) -> bool:
        """Return whether keyboard input is allowed."""

    def allows_wheel(self) -> bool:
        """Return whether wheel input is allowed."""

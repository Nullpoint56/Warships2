"""Public interaction-mode API contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InteractionMode:
    """Public interaction mode shape."""

    name: str
    allow_pointer: bool = True
    allow_keyboard: bool = True
    allow_wheel: bool = True


class InteractionModeMachine(ABC):
    """Public interaction mode machine contract."""

    @property
    @property
    @abstractmethod
    def current_mode(self) -> str:
        """Return current mode name."""

    @abstractmethod
    def register(self, mode: InteractionMode) -> None:
        """Register/replace mode."""

    @abstractmethod
    def set_mode(self, mode_name: str) -> None:
        """Switch mode."""

    @abstractmethod
    def allows_pointer(self) -> bool:
        """Return whether pointer input is allowed."""

    @abstractmethod
    def allows_keyboard(self) -> bool:
        """Return whether keyboard input is allowed."""

    @abstractmethod
    def allows_wheel(self) -> bool:
        """Return whether wheel input is allowed."""

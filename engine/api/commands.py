"""Public command-mapping API contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Command:
    """Resolved command token."""

    name: str


class CommandMap(ABC):
    """Public input-to-command mapping contract."""

    @abstractmethod
    def bind_key_down(self, key_name: str, command_name: str) -> None:
        """Bind normalized key-down input to command."""

    @abstractmethod
    def bind_char(self, char_value: str, command_name: str) -> None:
        """Bind char input to command."""

    @abstractmethod
    def bind_pointer_down(self, button: int, command_name: str) -> None:
        """Bind pointer-down button to command."""

    @abstractmethod
    def resolve_key_event(self, event_type: str, value: str) -> Command | None:
        """Resolve key/char event to command."""

    @abstractmethod
    def resolve_pointer_event(self, event_type: str, button: int) -> Command | None:
        """Resolve pointer event to command."""

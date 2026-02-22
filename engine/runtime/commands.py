"""Input-to-command mapping primitives."""

from __future__ import annotations

from engine.api.commands import Command, CommandMap


class RuntimeCommandMap(CommandMap):
    """Maps raw input triggers to engine-neutral command tokens."""

    def __init__(self) -> None:
        self._key_down_bindings: dict[str, str] = {}
        self._char_bindings: dict[str, str] = {}
        self._pointer_down_bindings: dict[int, str] = {}

    def bind_key_down(self, key_name: str, command_name: str) -> None:
        """Bind normalized key-down value to command name."""
        normalized = key_name.strip().lower()
        if not normalized:
            raise ValueError("key_name must not be empty")
        self._key_down_bindings[normalized] = command_name

    def bind_char(self, char_value: str, command_name: str) -> None:
        """Bind char input value to command name."""
        if not char_value:
            raise ValueError("char_value must not be empty")
        self._char_bindings[char_value] = command_name

    def bind_pointer_down(self, button: int, command_name: str) -> None:
        """Bind pointer-down mouse button to command name."""
        if button < 0:
            raise ValueError("button must be >= 0")
        self._pointer_down_bindings[button] = command_name

    def resolve_key_event(self, event_type: str, value: str) -> Command | None:
        """Resolve key/char input into a command token."""
        if event_type == "key_down":
            command_name = self._key_down_bindings.get(value.strip().lower())
            return Command(command_name) if command_name is not None else None
        if event_type == "char":
            command_name = self._char_bindings.get(value)
            return Command(command_name) if command_name is not None else None
        return None

    def resolve_pointer_event(self, event_type: str, button: int) -> Command | None:
        """Resolve pointer input into a command token."""
        if event_type != "pointer_down":
            return None
        command_name = self._pointer_down_bindings.get(button)
        return Command(command_name) if command_name is not None else None

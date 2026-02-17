from __future__ import annotations

import pytest

from engine.runtime.commands import CommandMap


def test_command_map_resolves_key_and_char_commands() -> None:
    commands = CommandMap()
    commands.bind_key_down("Enter", "confirm")
    commands.bind_char("x", "type_x")

    key_command = commands.resolve_key_event("key_down", "enter")
    char_command = commands.resolve_key_event("char", "x")

    assert key_command is not None
    assert key_command.name == "confirm"
    assert char_command is not None
    assert char_command.name == "type_x"


def test_command_map_resolves_pointer_command() -> None:
    commands = CommandMap()
    commands.bind_pointer_down(1, "primary_click")
    pointer_command = commands.resolve_pointer_event("pointer_down", 1)
    assert pointer_command is not None
    assert pointer_command.name == "primary_click"


def test_command_map_returns_none_for_unbound_events() -> None:
    commands = CommandMap()
    assert commands.resolve_key_event("key_down", "space") is None
    assert commands.resolve_key_event("key_up", "space") is None
    assert commands.resolve_pointer_event("pointer_up", 1) is None


def test_command_map_validates_binding_inputs() -> None:
    commands = CommandMap()
    with pytest.raises(ValueError):
        commands.bind_key_down("   ", "noop")
    with pytest.raises(ValueError):
        commands.bind_char("", "noop")
    with pytest.raises(ValueError):
        commands.bind_pointer_down(-1, "noop")

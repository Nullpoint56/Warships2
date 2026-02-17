from __future__ import annotations

import pytest

from engine.runtime.interaction_modes import InteractionMode, InteractionModeMachine


def test_interaction_mode_machine_defaults() -> None:
    modes = InteractionModeMachine()
    assert modes.current_mode == "default"
    assert modes.allows_pointer()
    assert modes.allows_keyboard()
    assert modes.allows_wheel()


def test_interaction_mode_machine_switches_modes() -> None:
    modes = InteractionModeMachine()
    modes.set_mode("modal")
    assert modes.current_mode == "modal"
    assert modes.allows_pointer()
    assert modes.allows_keyboard()
    assert not modes.allows_wheel()


def test_interaction_mode_machine_registers_custom_modes() -> None:
    modes = InteractionModeMachine()
    modes.register(InteractionMode("locked", allow_pointer=False, allow_keyboard=True))
    modes.set_mode("locked")
    assert not modes.allows_pointer()
    assert modes.allows_keyboard()
    assert modes.allows_wheel()


def test_interaction_mode_machine_validates_mode_inputs() -> None:
    modes = InteractionModeMachine()
    with pytest.raises(ValueError):
        modes.register(InteractionMode(name="   "))
    with pytest.raises(KeyError):
        modes.set_mode("missing")

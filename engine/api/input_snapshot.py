"""Immutable input snapshot contracts."""

from __future__ import annotations

from dataclasses import dataclass, field

from engine.api.input_events import KeyEvent, PointerEvent, WheelEvent


@dataclass(frozen=True, slots=True)
class KeyboardSnapshot:
    """Frame-stable keyboard state."""

    pressed_keys: frozenset[str] = field(default_factory=frozenset)
    just_pressed_keys: frozenset[str] = field(default_factory=frozenset)
    just_released_keys: frozenset[str] = field(default_factory=frozenset)
    text_input: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MouseSnapshot:
    """Frame-stable mouse/pointer state."""

    x: float = 0.0
    y: float = 0.0
    delta_x: float = 0.0
    delta_y: float = 0.0
    wheel_delta: float = 0.0
    pressed_buttons: frozenset[int] = field(default_factory=frozenset)
    just_pressed_buttons: frozenset[int] = field(default_factory=frozenset)
    just_released_buttons: frozenset[int] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class ControllerSnapshot:
    """Frame-stable controller state."""

    device_id: str
    connected: bool = True
    pressed_buttons: frozenset[str] = field(default_factory=frozenset)
    axes: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class ActionSnapshot:
    """Resolved logical action state for one frame."""

    active: frozenset[str] = field(default_factory=frozenset)
    just_started: frozenset[str] = field(default_factory=frozenset)
    just_ended: frozenset[str] = field(default_factory=frozenset)
    values: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True, slots=True)
class InputSnapshot:
    """Immutable frame input snapshot consumed by simulation."""

    frame_index: int
    keyboard: KeyboardSnapshot = field(default_factory=KeyboardSnapshot)
    mouse: MouseSnapshot = field(default_factory=MouseSnapshot)
    controllers: tuple[ControllerSnapshot, ...] = ()
    actions: ActionSnapshot = field(default_factory=ActionSnapshot)
    pointer_events: tuple[PointerEvent, ...] = ()
    key_events: tuple[KeyEvent, ...] = ()
    wheel_events: tuple[WheelEvent, ...] = ()


def create_empty_input_snapshot(*, frame_index: int = 0) -> InputSnapshot:
    """Create an empty input snapshot for bootstrap and tests."""
    return InputSnapshot(frame_index=frame_index)


__all__ = [
    "ActionSnapshot",
    "ControllerSnapshot",
    "InputSnapshot",
    "KeyboardSnapshot",
    "MouseSnapshot",
    "create_empty_input_snapshot",
]

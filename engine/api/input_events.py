"""Public input event types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PointerEvent:
    """Raw pointer event in canvas coordinates."""

    event_type: str
    x: float
    y: float
    button: int


@dataclass(frozen=True, slots=True)
class KeyEvent:
    """Raw key/char event."""

    event_type: str
    value: str


@dataclass(frozen=True, slots=True)
class WheelEvent:
    """Mouse wheel event in canvas coordinates."""

    x: float
    y: float
    dy: float


__all__ = ["KeyEvent", "PointerEvent", "WheelEvent"]

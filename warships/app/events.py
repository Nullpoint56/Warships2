"""Application event model."""

from __future__ import annotations

from dataclasses import dataclass

from warships.core.models import Coord


@dataclass(frozen=True, slots=True)
class ButtonPressed:
    """UI button pressed event."""

    button_id: str


@dataclass(frozen=True, slots=True)
class BoardCellPressed:
    """Board cell click event."""

    is_ai_board: bool
    coord: Coord


@dataclass(frozen=True, slots=True)
class PointerMoved:
    """Pointer moved in design coordinates."""

    x: float
    y: float


@dataclass(frozen=True, slots=True)
class PointerReleased:
    """Pointer released in design coordinates."""

    x: float
    y: float
    button: int


@dataclass(frozen=True, slots=True)
class KeyPressed:
    """Key down event."""

    key: str


@dataclass(frozen=True, slots=True)
class CharTyped:
    """Character input event."""

    char: str


@dataclass(frozen=True, slots=True)
class WheelScrolled:
    """Mouse wheel delta at design-space position."""

    x: float
    y: float
    dy: float

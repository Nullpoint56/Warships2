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

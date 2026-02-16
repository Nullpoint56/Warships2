"""Shot outcome evaluation (miss/hit/sunk/repeat)."""

from __future__ import annotations

from warships.game.core.board import BoardState
from warships.game.core.models import Coord, ShotResult, ShipType


def resolve_shot(board: BoardState, coord: Coord) -> tuple[ShotResult, ShipType | None]:
    """Resolve a shot against a board."""
    return board.apply_shot(coord)


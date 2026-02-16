"""Placement geometry helpers shared across app-layer flows."""

from __future__ import annotations

from warships.game.core.models import Coord, Orientation, ShipPlacement


def grab_index_from_cell(placement: ShipPlacement, cell: Coord) -> int:
    """Compute relative grab index inside a ship from a clicked cell."""
    if placement.orientation is Orientation.HORIZONTAL:
        return max(0, cell.col - placement.bow.col)
    return max(0, cell.row - placement.bow.row)


def bow_from_grab_index(cell: Coord, orientation: Orientation, grab_index: int) -> Coord:
    """Resolve bow coordinate from grabbed cell and relative index."""
    if orientation is Orientation.HORIZONTAL:
        return Coord(row=cell.row, col=cell.col - grab_index)
    return Coord(row=cell.row - grab_index, col=cell.col)

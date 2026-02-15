"""Placement geometry helpers shared across app-layer flows."""

from __future__ import annotations

from warships.core.models import Coord, Orientation, ShipPlacement


def cells_for_ship(placement: ShipPlacement) -> list[Coord]:
    """Return all occupied cells for a ship placement."""
    cells: list[Coord] = []
    for offset in range(placement.ship_type.size):
        if placement.orientation is Orientation.HORIZONTAL:
            cells.append(Coord(row=placement.bow.row, col=placement.bow.col + offset))
        else:
            cells.append(Coord(row=placement.bow.row + offset, col=placement.bow.col))
    return cells


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


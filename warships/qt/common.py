"""Shared Qt UI helpers and constants."""

from __future__ import annotations

from warships.core.models import Coord, Orientation, ShipPlacement

DESIGN_W = 1200.0
DESIGN_H = 720.0


def cells_for_ship(placement: ShipPlacement) -> list[Coord]:
    cells: list[Coord] = []
    for offset in range(placement.ship_type.size):
        if placement.orientation is Orientation.HORIZONTAL:
            cells.append(Coord(row=placement.bow.row, col=placement.bow.col + offset))
        else:
            cells.append(Coord(row=placement.bow.row + offset, col=placement.bow.col))
    return cells


def status_color(status: str) -> str:
    low = status.lower()
    if any(word in low for word in ("failed", "error", "invalid", "cannot", "duplicate")):
        return "#fca5a5"
    if any(word in low for word in ("saved", "renamed", "deleted", "started", "placed", "selected", "generated", "win")):
        return "#86efac"
    return "#dbeafe"

"""Shared Qt UI helpers and constants."""

from __future__ import annotations

from warships.core.models import Coord, ShipPlacement, cells_for_placement

DESIGN_W = 1200.0
DESIGN_H = 720.0


def cells_for_ship(placement: ShipPlacement) -> list[Coord]:
    return cells_for_placement(placement)


def status_color(status: str) -> str:
    low = status.lower()
    if any(word in low for word in ("failed", "error", "invalid", "cannot", "duplicate")):
        return "#fca5a5"
    if any(word in low for word in ("saved", "renamed", "deleted", "started", "placed", "selected", "generated", "win")):
        return "#86efac"
    return "#dbeafe"

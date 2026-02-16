"""Engine-owned geometry primitives."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Rect:
    """Simple axis-aligned rectangle."""

    x: float
    y: float
    w: float
    h: float

    def contains(self, px: float, py: float) -> bool:
        """Return whether a point is inside the rectangle."""
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h


@dataclass(frozen=True, slots=True)
class CellCoord:
    """Grid cell coordinate in row/column space."""

    row: int
    col: int

"""Core domain models used by game logic."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

BOARD_SIZE = 10


class Orientation(StrEnum):
    """Ship orientation."""

    HORIZONTAL = "HORIZONTAL"
    VERTICAL = "VERTICAL"


class ShipType(StrEnum):
    """Classic Battleship ship types."""

    CARRIER = "CARRIER"
    BATTLESHIP = "BATTLESHIP"
    CRUISER = "CRUISER"
    SUBMARINE = "SUBMARINE"
    DESTROYER = "DESTROYER"

    @property
    def size(self) -> int:
        return SHIP_LENGTHS[self]


SHIP_LENGTHS: dict[ShipType, int] = {
    ShipType.CARRIER: 5,
    ShipType.BATTLESHIP: 4,
    ShipType.CRUISER: 3,
    ShipType.SUBMARINE: 3,
    ShipType.DESTROYER: 2,
}

DEFAULT_FLEET: tuple[ShipType, ...] = (
    ShipType.CARRIER,
    ShipType.BATTLESHIP,
    ShipType.CRUISER,
    ShipType.SUBMARINE,
    ShipType.DESTROYER,
)


class ShotResult(StrEnum):
    """Result of a single shot."""

    MISS = "MISS"
    HIT = "HIT"
    SUNK = "SUNK"
    REPEAT = "REPEAT"
    INVALID = "INVALID"


class Turn(StrEnum):
    """Current turn owner."""

    PLAYER = "PLAYER"
    AI = "AI"


@dataclass(frozen=True, slots=True)
class Coord:
    """Board coordinate."""

    row: int
    col: int


@dataclass(frozen=True, slots=True)
class ShipPlacement:
    """Placement of a single ship."""

    ship_type: ShipType
    bow: Coord
    orientation: Orientation


@dataclass(slots=True)
class FleetPlacement:
    """Collection of ship placements."""

    ships: list[ShipPlacement]

    def by_type(self, ship_type: ShipType) -> ShipPlacement | None:
        """Find ship placement for the given type."""
        for ship in self.ships:
            if ship.ship_type == ship_type:
                return ship
        return None


def cells_for_placement(placement: ShipPlacement) -> list[Coord]:
    """Compute occupied cells for a ship placement."""
    result: list[Coord] = []
    for i in range(placement.ship_type.size):
        if placement.orientation is Orientation.HORIZONTAL:
            result.append(Coord(placement.bow.row, placement.bow.col + i))
        else:
            result.append(Coord(placement.bow.row + i, placement.bow.col))
    return result

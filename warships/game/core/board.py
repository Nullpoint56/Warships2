"""Board state representation and mutation helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from warships.game.core.models import (
    BOARD_SIZE,
    Coord,
    ShipPlacement,
    ShipType,
    ShotResult,
    cells_for_placement,
)


@dataclass(slots=True)
class BoardState:
    """Numpy-backed board state."""

    size: int = BOARD_SIZE
    ships: np.ndarray = field(
        default_factory=lambda: np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=np.int16)
    )
    shots: np.ndarray = field(
        default_factory=lambda: np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=np.int8)
    )
    ship_cells: dict[int, list[Coord]] = field(default_factory=dict)
    ship_types: dict[int, ShipType] = field(default_factory=dict)
    ship_remaining: dict[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.ships.shape != (self.size, self.size):
            self.ships = np.zeros((self.size, self.size), dtype=np.int16)
        if self.shots.shape != (self.size, self.size):
            self.shots = np.zeros((self.size, self.size), dtype=np.int8)

    def in_bounds(self, coord: Coord) -> bool:
        """Return whether the coordinate is in board bounds."""
        return 0 <= coord.row < self.size and 0 <= coord.col < self.size

    def can_place(self, placement: ShipPlacement) -> bool:
        """Return whether a placement is valid and non-overlapping."""
        for cell in cells_for_placement(placement):
            if not self.in_bounds(cell):
                return False
            if self.ships[cell.row, cell.col] != 0:
                return False
        return True

    def place_ship(self, ship_id: int, placement: ShipPlacement) -> None:
        """Place a ship on the board."""
        if not self.can_place(placement):
            raise ValueError(f"Invalid placement for {placement.ship_type.value}.")
        cells = cells_for_placement(placement)
        for cell in cells:
            self.ships[cell.row, cell.col] = ship_id
        self.ship_cells[ship_id] = cells
        self.ship_types[ship_id] = placement.ship_type
        self.ship_remaining[ship_id] = len(cells)

    def was_shot(self, coord: Coord) -> bool:
        """Return whether this cell was previously targeted."""
        return self.shots[coord.row, coord.col] != 0

    def apply_shot(self, coord: Coord) -> tuple[ShotResult, ShipType | None]:
        """Apply a shot and return result + sunk ship type if any."""
        if not self.in_bounds(coord):
            return ShotResult.INVALID, None
        if self.was_shot(coord):
            return ShotResult.REPEAT, None

        ship_id = int(self.ships[coord.row, coord.col])
        if ship_id == 0:
            self.shots[coord.row, coord.col] = 1
            return ShotResult.MISS, None

        self.shots[coord.row, coord.col] = 2
        self.ship_remaining[ship_id] -= 1
        if self.ship_remaining[ship_id] == 0:
            return ShotResult.SUNK, self.ship_types[ship_id]
        return ShotResult.HIT, None

    def all_ships_sunk(self) -> bool:
        """Return whether every ship has been sunk."""
        return all(remaining == 0 for remaining in self.ship_remaining.values())

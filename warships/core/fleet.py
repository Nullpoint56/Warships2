"""Fleet placement validation and construction."""

from __future__ import annotations

import random

from warships.core.board import BoardState
from warships.core.models import BOARD_SIZE, DEFAULT_FLEET, Coord, FleetPlacement, Orientation, ShipPlacement, ShipType


def validate_fleet(fleet: FleetPlacement, size: int = BOARD_SIZE) -> tuple[bool, str]:
    """Validate whether a fleet exactly matches classic rules."""
    seen: set[ShipType] = set()
    board = BoardState(size=size)

    if len(fleet.ships) != len(DEFAULT_FLEET):
        return False, "Fleet must contain exactly five ships."

    for placement in fleet.ships:
        if placement.ship_type in seen:
            return False, f"Duplicate ship type: {placement.ship_type.value}."
        seen.add(placement.ship_type)
        if not board.can_place(placement):
            return False, f"Invalid placement for {placement.ship_type.value}."
        board.place_ship(len(seen), placement)

    missing = [ship for ship in DEFAULT_FLEET if ship not in seen]
    if missing:
        return False, f"Missing ships: {', '.join(ship.value for ship in missing)}."
    return True, ""


def build_board_from_fleet(fleet: FleetPlacement, size: int = BOARD_SIZE) -> BoardState:
    """Create a board state from a validated fleet placement."""
    valid, reason = validate_fleet(fleet, size=size)
    if not valid:
        raise ValueError(reason)
    board = BoardState(size=size)
    for idx, placement in enumerate(fleet.ships, start=1):
        board.place_ship(idx, placement)
    return board


def random_fleet(rng: random.Random, size: int = BOARD_SIZE) -> FleetPlacement:
    """Generate a random valid fleet placement."""
    board = BoardState(size=size)
    placements: list[ShipPlacement] = []

    for ship_type in DEFAULT_FLEET:
        placed = False
        for _ in range(10_000):
            orientation = rng.choice([Orientation.HORIZONTAL, Orientation.VERTICAL])
            row = rng.randrange(size)
            col = rng.randrange(size)
            placement = ShipPlacement(ship_type=ship_type, bow=Coord(row=row, col=col), orientation=orientation)
            if board.can_place(placement):
                board.place_ship(len(placements) + 1, placement)
                placements.append(placement)
                placed = True
                break
        if not placed:
            raise RuntimeError("Failed to generate random fleet placement.")

    return FleetPlacement(ships=placements)

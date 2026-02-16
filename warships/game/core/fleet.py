"""Fleet placement validation and construction."""

from __future__ import annotations

import random

from warships.game.core.board import BoardState
from warships.game.core.models import (
    BOARD_SIZE,
    DEFAULT_FLEET,
    Coord,
    FleetPlacement,
    Orientation,
    ShipPlacement,
    ShipType,
    cells_for_placement,
)


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
    """Generate a random valid fleet placement with non-touching ships."""
    for _ in range(400):
        generated = _generate_non_touching_fleet(rng, size)
        if generated is not None:
            return generated
    # Fallback preserves playability for atypical board sizes/configs.
    return _generate_relaxed_fleet(rng, size)


def _generate_non_touching_fleet(rng: random.Random, size: int) -> FleetPlacement | None:
    occupied: set[tuple[int, int]] = set()
    placements_by_type: dict[ShipType, ShipPlacement] = {}
    ship_order = list(DEFAULT_FLEET)
    rng.shuffle(ship_order)

    for ship_type in ship_order:
        candidates = _candidate_placements(ship_type, size, occupied)
        if not candidates:
            return None
        placement = rng.choice(candidates)
        placements_by_type[ship_type] = placement
        for cell in cells_for_placement(placement):
            occupied.add((cell.row, cell.col))

    ordered = [placements_by_type[ship_type] for ship_type in DEFAULT_FLEET]
    return FleetPlacement(ships=ordered)


def _candidate_placements(
    ship_type: ShipType,
    size: int,
    occupied: set[tuple[int, int]],
) -> list[ShipPlacement]:
    candidates: list[ShipPlacement] = []
    for orientation in (Orientation.HORIZONTAL, Orientation.VERTICAL):
        max_row = size if orientation is Orientation.HORIZONTAL else size - ship_type.size + 1
        max_col = size - ship_type.size + 1 if orientation is Orientation.HORIZONTAL else size
        for row in range(max_row):
            for col in range(max_col):
                placement = ShipPlacement(
                    ship_type=ship_type, bow=Coord(row=row, col=col), orientation=orientation
                )
                cells = cells_for_placement(placement)
                if _touches_existing(cells, occupied, size):
                    continue
                candidates.append(placement)
    return candidates


def _touches_existing(cells: list[Coord], occupied: set[tuple[int, int]], size: int) -> bool:
    for cell in cells:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                rr = cell.row + dr
                cc = cell.col + dc
                if not (0 <= rr < size and 0 <= cc < size):
                    continue
                if (rr, cc) in occupied:
                    return True
    return False


def _generate_relaxed_fleet(rng: random.Random, size: int) -> FleetPlacement:
    """Legacy overlap-only generator used as a last resort."""
    board = BoardState(size=size)
    placements: list[ShipPlacement] = []

    for ship_type in DEFAULT_FLEET:
        placed = False
        for _ in range(10_000):
            orientation = rng.choice([Orientation.HORIZONTAL, Orientation.VERTICAL])
            row = rng.randrange(size)
            col = rng.randrange(size)
            placement = ShipPlacement(
                ship_type=ship_type, bow=Coord(row=row, col=col), orientation=orientation
            )
            if board.can_place(placement):
                board.place_ship(len(placements) + 1, placement)
                placements.append(placement)
                placed = True
                break
        if not placed:
            raise RuntimeError("Failed to generate random fleet placement.")

    return FleetPlacement(ships=placements)

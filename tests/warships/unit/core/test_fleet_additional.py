import random

from warships.game.core.fleet import _generate_relaxed_fleet, build_board_from_fleet, random_fleet, validate_fleet
from warships.game.core.models import Coord, FleetPlacement, Orientation, ShipPlacement, ShipType


def test_validate_fleet_rejects_missing_ship() -> None:
    fleet = FleetPlacement(
        ships=[
            ShipPlacement(ShipType.CARRIER, Coord(0, 0), Orientation.HORIZONTAL),
            ShipPlacement(ShipType.BATTLESHIP, Coord(2, 0), Orientation.HORIZONTAL),
            ShipPlacement(ShipType.CRUISER, Coord(4, 0), Orientation.HORIZONTAL),
            ShipPlacement(ShipType.SUBMARINE, Coord(6, 0), Orientation.HORIZONTAL),
        ]
    )
    valid, reason = validate_fleet(fleet)
    assert not valid
    assert "exactly five ships" in reason


def test_build_board_from_fleet_success(valid_fleet) -> None:
    board = build_board_from_fleet(valid_fleet)
    assert board.ship_remaining


def test_random_fleet_and_relaxed_fleet_paths() -> None:
    rng = random.Random(9)
    fleet = random_fleet(rng)
    assert validate_fleet(fleet)[0]
    relaxed = _generate_relaxed_fleet(random.Random(10), 10)
    assert validate_fleet(relaxed)[0]

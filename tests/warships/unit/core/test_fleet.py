from warships.game.core.fleet import build_board_from_fleet, random_fleet, validate_fleet
from warships.game.core.models import Coord, FleetPlacement, Orientation, ShipPlacement, ShipType


def test_validate_fleet_accepts_valid_fleet(valid_fleet: FleetPlacement) -> None:
    valid, reason = validate_fleet(valid_fleet)
    assert valid
    assert reason == ""


def test_validate_fleet_rejects_duplicate_ship_type() -> None:
    fleet = FleetPlacement(
        ships=[
            ShipPlacement(ShipType.CARRIER, Coord(0, 0), Orientation.HORIZONTAL),
            ShipPlacement(ShipType.CARRIER, Coord(2, 0), Orientation.HORIZONTAL),
            ShipPlacement(ShipType.CRUISER, Coord(4, 0), Orientation.HORIZONTAL),
            ShipPlacement(ShipType.SUBMARINE, Coord(6, 0), Orientation.HORIZONTAL),
            ShipPlacement(ShipType.DESTROYER, Coord(8, 0), Orientation.HORIZONTAL),
        ]
    )
    valid, reason = validate_fleet(fleet)
    assert not valid
    assert "Duplicate ship type" in reason


def test_build_board_from_fleet_raises_on_invalid() -> None:
    invalid = FleetPlacement(ships=[ShipPlacement(ShipType.DESTROYER, Coord(0, 9), Orientation.HORIZONTAL)])
    try:
        build_board_from_fleet(invalid)
    except ValueError:
        assert True
    else:
        assert False


def test_random_fleet_is_valid(seeded_rng) -> None:
    fleet = random_fleet(seeded_rng)
    valid, reason = validate_fleet(fleet)
    assert valid, reason

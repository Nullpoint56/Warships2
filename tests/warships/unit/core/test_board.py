from warships.game.core.board import BoardState
from warships.game.core.models import Coord, Orientation, ShipPlacement, ShipType, ShotResult


def test_board_can_place_and_reject_overlap_or_oob() -> None:
    board = BoardState()
    carrier = ShipPlacement(ShipType.CARRIER, Coord(0, 0), Orientation.HORIZONTAL)
    assert board.can_place(carrier)
    board.place_ship(1, carrier)
    assert not board.can_place(
        ShipPlacement(ShipType.DESTROYER, Coord(0, 0), Orientation.HORIZONTAL)
    )
    assert not board.can_place(ShipPlacement(ShipType.CARRIER, Coord(0, 8), Orientation.HORIZONTAL))
    # Ships cannot touch, including diagonally.
    assert not board.can_place(ShipPlacement(ShipType.DESTROYER, Coord(1, 5), Orientation.HORIZONTAL))


def test_board_apply_shot_states() -> None:
    board = BoardState()
    destroyer = ShipPlacement(ShipType.DESTROYER, Coord(1, 1), Orientation.HORIZONTAL)
    board.place_ship(1, destroyer)

    miss, _ = board.apply_shot(Coord(0, 0))
    assert miss is ShotResult.MISS
    repeat, _ = board.apply_shot(Coord(0, 0))
    assert repeat is ShotResult.REPEAT

    hit, sunk = board.apply_shot(Coord(1, 1))
    assert hit is ShotResult.HIT and sunk is None
    sunk_result, sunk_type = board.apply_shot(Coord(1, 2))
    assert sunk_result is ShotResult.SUNK and sunk_type is ShipType.DESTROYER
    assert board.all_ships_sunk()

    invalid, _ = board.apply_shot(Coord(-1, 0))
    assert invalid is ShotResult.INVALID

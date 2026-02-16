from warships.game.core.board import BoardState
from warships.game.core.models import Coord, Orientation, ShipPlacement, ShipType, ShotResult
from warships.game.core.shot_resolution import resolve_shot


def test_resolve_shot_proxies_board_apply() -> None:
    board = BoardState()
    board.place_ship(1, ShipPlacement(ShipType.DESTROYER, Coord(0, 0), Orientation.HORIZONTAL))
    result, sunk = resolve_shot(board, Coord(0, 0))
    assert result is ShotResult.HIT
    assert sunk is None

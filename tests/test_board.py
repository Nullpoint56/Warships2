"""Tests for board representation behavior."""

from warships.core.board import BoardState
from warships.core.models import Coord, Orientation, ShipPlacement, ShipType, ShotResult


def test_apply_shot_miss_then_repeat() -> None:
    board = BoardState()
    result, sunk = board.apply_shot(Coord(0, 0))
    assert result is ShotResult.MISS
    assert sunk is None

    repeat, _ = board.apply_shot(Coord(0, 0))
    assert repeat is ShotResult.REPEAT


def test_apply_shot_hit_and_sink() -> None:
    board = BoardState()
    placement = ShipPlacement(ship_type=ShipType.DESTROYER, bow=Coord(0, 0), orientation=Orientation.HORIZONTAL)
    board.place_ship(1, placement)

    first, _ = board.apply_shot(Coord(0, 0))
    second, sunk = board.apply_shot(Coord(0, 1))
    assert first is ShotResult.HIT
    assert second is ShotResult.SUNK
    assert sunk is ShipType.DESTROYER

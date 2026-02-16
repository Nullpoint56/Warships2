from warships.game.app.flows.placement_math import bow_from_grab_index, grab_index_from_cell
from warships.game.core.models import Coord, Orientation, ShipPlacement, ShipType


def test_grab_index_from_cell_horizontal_and_vertical() -> None:
    h = ShipPlacement(ShipType.CARRIER, Coord(1, 2), Orientation.HORIZONTAL)
    v = ShipPlacement(ShipType.CARRIER, Coord(1, 2), Orientation.VERTICAL)
    assert grab_index_from_cell(h, Coord(1, 4)) == 2
    assert grab_index_from_cell(v, Coord(4, 2)) == 3


def test_bow_from_grab_index() -> None:
    assert bow_from_grab_index(Coord(5, 7), Orientation.HORIZONTAL, 2) == Coord(5, 5)
    assert bow_from_grab_index(Coord(5, 7), Orientation.VERTICAL, 2) == Coord(3, 7)

from warships.game.core.models import (
    Coord,
    Orientation,
    ShipPlacement,
    ShipType,
    cells_for_placement,
)


def test_ship_type_size_mapping() -> None:
    assert ShipType.CARRIER.size == 5
    assert ShipType.DESTROYER.size == 2


def test_cells_for_placement_horizontal_and_vertical() -> None:
    horizontal = ShipPlacement(ShipType.CRUISER, Coord(1, 2), Orientation.HORIZONTAL)
    vertical = ShipPlacement(ShipType.CRUISER, Coord(1, 2), Orientation.VERTICAL)
    assert cells_for_placement(horizontal) == [Coord(1, 2), Coord(1, 3), Coord(1, 4)]
    assert cells_for_placement(vertical) == [Coord(1, 2), Coord(2, 2), Coord(3, 2)]

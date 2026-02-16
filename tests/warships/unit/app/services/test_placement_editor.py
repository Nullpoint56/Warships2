from engine.ui_runtime.grid_layout import GridLayout
from warships.game.app.services.placement_editor import PlacementEditorService
from warships.game.core.models import Coord, Orientation, ShipPlacement, ShipType
from warships.game.ui.layout_metrics import PLACEMENT_PANEL


def test_reset_and_all_ships_placed() -> None:
    ship_order = [ShipType.CARRIER, ShipType.DESTROYER]
    placements = PlacementEditorService.reset(ship_order)
    assert set(placements.keys()) == set(ship_order)
    assert not PlacementEditorService.all_ships_placed(placements, ship_order)
    placements[ShipType.CARRIER] = ShipPlacement(
        ShipType.CARRIER, Coord(0, 0), Orientation.HORIZONTAL
    )
    placements[ShipType.DESTROYER] = ShipPlacement(
        ShipType.DESTROYER, Coord(2, 0), Orientation.HORIZONTAL
    )
    assert PlacementEditorService.all_ships_placed(placements, ship_order)


def test_can_place_and_reject_duplicate_or_overlap() -> None:
    placements = {
        ShipType.CARRIER: ShipPlacement(ShipType.CARRIER, Coord(0, 0), Orientation.HORIZONTAL),
        ShipType.DESTROYER: None,
    }
    candidate_ok = ShipPlacement(ShipType.DESTROYER, Coord(2, 0), Orientation.HORIZONTAL)
    assert PlacementEditorService.can_place(placements, candidate_ok)
    candidate_overlap = ShipPlacement(ShipType.DESTROYER, Coord(0, 1), Orientation.HORIZONTAL)
    assert not PlacementEditorService.can_place(placements, candidate_overlap)


def test_to_primary_grid_cell_and_palette_lookup() -> None:
    layout = GridLayout()
    coord = PlacementEditorService.to_primary_grid_cell(layout, 81.0, 151.0)
    assert coord == Coord(0, 0)
    assert PlacementEditorService.to_primary_grid_cell(layout, 10.0, 10.0) is None

    ship_order = [ShipType.CARRIER, ShipType.BATTLESHIP]
    row0 = PLACEMENT_PANEL.row_rect(0)
    picked = PlacementEditorService.palette_ship_at_point(ship_order, row0.x + 1.0, row0.y + 1.0)
    assert picked is ShipType.CARRIER
    assert PlacementEditorService.palette_ship_at_point(ship_order, 0.0, 0.0) is None

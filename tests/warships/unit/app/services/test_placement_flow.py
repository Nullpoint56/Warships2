from engine.ui_runtime.grid_layout import GridLayout
from warships.game.app.services.placement_flow import HeldShipState, PlacementFlowService
from warships.game.core.models import Coord, Orientation, ShipPlacement, ShipType
from warships.game.ui.layout_metrics import PLACEMENT_PANEL


def _empty_placements() -> dict[ShipType, ShipPlacement | None]:
    return {
        ShipType.CARRIER: None,
        ShipType.BATTLESHIP: None,
        ShipType.CRUISER: None,
        ShipType.SUBMARINE: None,
        ShipType.DESTROYER: None,
    }


def test_on_key_for_held_rotate_delete_and_noop() -> None:
    held = HeldShipState(
        ship_type=ShipType.DESTROYER,
        orientation=Orientation.HORIZONTAL,
        previous=None,
        grab_index=0,
    )
    rotate = PlacementFlowService.on_key_for_held(key="r", held_state=held)
    assert rotate.handled
    assert rotate.held_state.orientation is Orientation.VERTICAL
    delete = PlacementFlowService.on_key_for_held(key="d", held_state=held)
    assert delete.handled
    assert delete.held_state.ship_type is None
    noop = PlacementFlowService.on_key_for_held(key="x", held_state=held)
    assert not noop.handled


def test_on_pointer_release_places_ship_or_restores() -> None:
    placements = _empty_placements()
    layout = GridLayout()
    held = HeldShipState(
        ship_type=ShipType.DESTROYER,
        orientation=Orientation.HORIZONTAL,
        previous=None,
        grab_index=0,
    )
    placed = PlacementFlowService.on_pointer_release(
        placements_by_type=placements,
        held_state=held,
        layout=layout,
        x=layout.primary_origin_x + 1,
        y=layout.origin_y + 1,
    )
    assert placed.handled
    assert placements[ShipType.DESTROYER] is not None
    assert placed.held_state.ship_type is None

    previous = ShipPlacement(ShipType.DESTROYER, Coord(3, 3), Orientation.HORIZONTAL)
    placements[ShipType.DESTROYER] = None
    restore = PlacementFlowService.on_pointer_release(
        placements_by_type=placements,
        held_state=HeldShipState(
            ship_type=ShipType.DESTROYER,
            orientation=Orientation.HORIZONTAL,
            previous=previous,
            grab_index=0,
        ),
        layout=layout,
        x=0,
        y=0,
    )
    assert restore.handled
    assert placements[ShipType.DESTROYER] == previous


def test_on_pointer_release_reports_touching_rule_violation() -> None:
    placements = _empty_placements()
    layout = GridLayout()
    placements[ShipType.CARRIER] = ShipPlacement(ShipType.CARRIER, Coord(0, 0), Orientation.HORIZONTAL)
    held = HeldShipState(
        ship_type=ShipType.DESTROYER,
        orientation=Orientation.HORIZONTAL,
        previous=None,
        grab_index=0,
    )
    # Drop DESTROYER adjacent to CARRIER with diagonal/edge contact.
    result = PlacementFlowService.on_pointer_release(
        placements_by_type=placements,
        held_state=held,
        layout=layout,
        x=layout.primary_origin_x + (5 * layout.cell_size) + 1,
        y=layout.origin_y + 1,
    )
    assert result.handled
    assert result.status == "Ships cannot touch, even diagonally. Leave one-cell gap."


def test_pointer_down_paths_pick_palette_and_right_click_remove() -> None:
    placements = _empty_placements()
    layout = GridLayout()
    ship_order = [
        ShipType.CARRIER,
        ShipType.BATTLESHIP,
        ShipType.CRUISER,
        ShipType.SUBMARINE,
        ShipType.DESTROYER,
    ]
    row0 = PLACEMENT_PANEL.row_rect(0)
    pick = PlacementFlowService.on_left_pointer_down(
        ship_order=ship_order,
        placements_by_type=placements,
        held_state=HeldShipState(None, None, None, 0),
        layout=layout,
        x=row0.x + 1,
        y=row0.y + 1,
    )
    assert pick.handled
    assert pick.held_state.ship_type is ShipType.CARRIER

    placements[ShipType.DESTROYER] = ShipPlacement(
        ShipType.DESTROYER, Coord(0, 0), Orientation.HORIZONTAL
    )
    removed = PlacementFlowService.on_right_pointer_down(
        placements_by_type=placements,
        held_state=HeldShipState(None, None, None, 0),
        layout=layout,
        x=layout.primary_origin_x + 1,
        y=layout.origin_y + 1,
    )
    assert removed.handled
    assert placements[ShipType.DESTROYER] is None

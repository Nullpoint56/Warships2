from engine.ui_runtime.grid_layout import GridLayout
from warships.game.app.services.placement_flow import HeldShipState, PlacementFlowService
from warships.game.core.models import Coord, Orientation, ShipPlacement, ShipType


def _placements() -> dict[ShipType, ShipPlacement | None]:
    return {
        ShipType.CARRIER: None,
        ShipType.BATTLESHIP: None,
        ShipType.CRUISER: None,
        ShipType.SUBMARINE: None,
        ShipType.DESTROYER: None,
    }


def test_restore_held_ship_and_unhandled_paths() -> None:
    placements = _placements()
    previous = ShipPlacement(ShipType.DESTROYER, Coord(1, 1), Orientation.HORIZONTAL)
    restored = PlacementFlowService.restore_held_ship(
        placements,
        HeldShipState(ShipType.DESTROYER, Orientation.HORIZONTAL, previous, 0),
    )
    assert restored.ship_type is None
    assert placements[ShipType.DESTROYER] == previous

    no_hold = PlacementFlowService.on_pointer_release(
        placements_by_type=placements,
        held_state=HeldShipState(None, None, None, 0),
        layout=GridLayout(),
        x=0,
        y=0,
    )
    assert not no_hold.handled


def test_left_pointer_down_pick_from_board_and_already_placed_palette() -> None:
    placements = _placements()
    placed = ShipPlacement(ShipType.DESTROYER, Coord(0, 0), Orientation.HORIZONTAL)
    placements[ShipType.DESTROYER] = placed
    layout = GridLayout()

    pick = PlacementFlowService.on_left_pointer_down(
        ship_order=list(placements.keys()),
        placements_by_type=placements,
        held_state=HeldShipState(None, None, None, 0),
        layout=layout,
        x=layout.primary_origin_x + 1,
        y=layout.origin_y + 1,
    )
    assert pick.handled
    assert pick.held_state.ship_type is ShipType.DESTROYER

    placements[ShipType.CARRIER] = ShipPlacement(ShipType.CARRIER, Coord(2, 0), Orientation.HORIZONTAL)
    from warships.game.ui.layout_metrics import PLACEMENT_PANEL

    row = PLACEMENT_PANEL.row_rect(0)
    already = PlacementFlowService.on_left_pointer_down(
        ship_order=[ShipType.CARRIER],
        placements_by_type=placements,
        held_state=HeldShipState(None, None, None, 0),
        layout=layout,
        x=row.x + 1,
        y=row.y + 1,
    )
    assert already.handled
    assert "already placed" in (already.status or "")


def test_pointer_release_invalid_drop_and_right_click_non_hit_paths() -> None:
    placements = _placements()
    layout = GridLayout()
    placements[ShipType.CARRIER] = ShipPlacement(ShipType.CARRIER, Coord(0, 0), Orientation.HORIZONTAL)

    invalid_drop = PlacementFlowService.on_pointer_release(
        placements_by_type=placements,
        held_state=HeldShipState(ShipType.DESTROYER, Orientation.HORIZONTAL, None, 0),
        layout=layout,
        x=layout.primary_origin_x + 1,
        y=layout.origin_y + 1,
    )
    assert invalid_drop.handled
    assert invalid_drop.status == "Invalid drop position."

    outside_board = PlacementFlowService.on_right_pointer_down(
        placements_by_type=placements,
        held_state=HeldShipState(None, None, None, 0),
        layout=layout,
        x=0,
        y=0,
    )
    assert not outside_board.handled

    inside_but_no_ship = PlacementFlowService.on_right_pointer_down(
        placements_by_type=placements,
        held_state=HeldShipState(None, None, None, 0),
        layout=layout,
        x=layout.primary_origin_x + (9 * layout.cell_size) + 1,
        y=layout.origin_y + (9 * layout.cell_size) + 1,
    )
    assert not inside_but_no_ship.handled


def test_key_and_right_click_when_holding_ship() -> None:
    placements = _placements()
    previous = ShipPlacement(ShipType.DESTROYER, Coord(2, 2), Orientation.VERTICAL)
    held = HeldShipState(ShipType.DESTROYER, Orientation.VERTICAL, previous, 1)

    no_ship = PlacementFlowService.on_key_for_held(key="r", held_state=HeldShipState(None, None, None, 0))
    assert not no_ship.handled

    returned = PlacementFlowService.on_right_pointer_down(
        placements_by_type=placements,
        held_state=held,
        layout=GridLayout(),
        x=0,
        y=0,
    )
    assert returned.handled
    assert returned.status == "Returned held ship."
    assert placements[ShipType.DESTROYER] == previous

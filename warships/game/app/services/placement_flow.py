"""Placement interaction flow helpers extracted from controller."""

from __future__ import annotations

from dataclasses import dataclass

from warships.game.app.flows.placement_math import bow_from_grab_index, grab_index_from_cell
from warships.game.app.services.placement_editor import PlacementEditorService
from warships.game.core.models import Orientation, ShipPlacement, ShipType, cells_for_placement
from engine.ui_runtime.board_layout import BoardLayout


@dataclass(frozen=True, slots=True)
class HeldShipState:
    """Held ship drag state in placement editor."""

    ship_type: ShipType | None
    orientation: Orientation | None
    previous: ShipPlacement | None
    grab_index: int


@dataclass(frozen=True, slots=True)
class PlacementActionResult:
    """Outcome of a placement interaction."""

    handled: bool
    held_state: HeldShipState
    status: str | None = None
    refresh_buttons: bool = False


class PlacementFlowService:
    """Placement editor interactions as pure-ish orchestration helpers."""

    @staticmethod
    def restore_held_ship(
        placements_by_type: dict[ShipType, ShipPlacement | None],
        held_state: HeldShipState,
    ) -> HeldShipState:
        if held_state.ship_type is not None and held_state.previous is not None:
            placements_by_type[held_state.ship_type] = held_state.previous
        return HeldShipState(ship_type=None, orientation=None, previous=None, grab_index=0)

    @staticmethod
    def on_pointer_release(
        *,
        placements_by_type: dict[ShipType, ShipPlacement | None],
        held_state: HeldShipState,
        layout: BoardLayout,
        x: float,
        y: float,
    ) -> PlacementActionResult:
        if held_state.ship_type is None or held_state.orientation is None:
            return PlacementActionResult(handled=False, held_state=held_state)
        target = PlacementEditorService.to_board_cell(layout, x, y)
        if target is None:
            return PlacementActionResult(
                handled=True,
                held_state=PlacementFlowService.restore_held_ship(placements_by_type, held_state),
                refresh_buttons=True,
            )
        bow = bow_from_grab_index(target, held_state.orientation, held_state.grab_index)
        candidate = ShipPlacement(held_state.ship_type, bow, held_state.orientation)
        if PlacementEditorService.can_place(placements_by_type, candidate):
            placements_by_type[held_state.ship_type] = candidate
            return PlacementActionResult(
                handled=True,
                held_state=HeldShipState(ship_type=None, orientation=None, previous=None, grab_index=0),
                status=f"Placed {held_state.ship_type.value}.",
                refresh_buttons=True,
            )
        return PlacementActionResult(
            handled=True,
            held_state=PlacementFlowService.restore_held_ship(placements_by_type, held_state),
            status="Invalid drop position.",
            refresh_buttons=True,
        )

    @staticmethod
    def on_key_for_held(*, key: str, held_state: HeldShipState) -> PlacementActionResult:
        if held_state.ship_type is None:
            return PlacementActionResult(handled=False, held_state=held_state)
        if key == "r":
            orientation = (
                Orientation.VERTICAL if held_state.orientation is Orientation.HORIZONTAL else Orientation.HORIZONTAL
            )
            next_state = HeldShipState(
                ship_type=held_state.ship_type,
                orientation=orientation,
                previous=held_state.previous,
                grab_index=held_state.grab_index,
            )
            return PlacementActionResult(
                handled=True,
                held_state=next_state,
                status=f"Holding {held_state.ship_type.value} ({orientation.value}).",
            )
        if key == "d":
            return PlacementActionResult(
                handled=True,
                held_state=HeldShipState(ship_type=None, orientation=None, previous=None, grab_index=0),
                status=f"Deleted {held_state.ship_type.value} from hand.",
                refresh_buttons=True,
            )
        return PlacementActionResult(handled=False, held_state=held_state)

    @staticmethod
    def on_right_pointer_down(
        *,
        placements_by_type: dict[ShipType, ShipPlacement | None],
        held_state: HeldShipState,
        layout: BoardLayout,
        x: float,
        y: float,
    ) -> PlacementActionResult:
        if held_state.ship_type is not None:
            return PlacementActionResult(
                handled=True,
                held_state=PlacementFlowService.restore_held_ship(placements_by_type, held_state),
                status="Returned held ship.",
                refresh_buttons=True,
            )
        board_cell = PlacementEditorService.to_board_cell(layout, x, y)
        if board_cell is None:
            return PlacementActionResult(handled=False, held_state=held_state)
        for ship_type, placement in placements_by_type.items():
            if placement is not None and board_cell in cells_for_placement(placement):
                placements_by_type[ship_type] = None
                return PlacementActionResult(
                    handled=True,
                    held_state=held_state,
                    status=f"Removed {ship_type.value}.",
                    refresh_buttons=True,
                )
        return PlacementActionResult(handled=False, held_state=held_state)

    @staticmethod
    def on_left_pointer_down(
        *,
        ship_order: tuple[ShipType, ...] | list[ShipType],
        placements_by_type: dict[ShipType, ShipPlacement | None],
        held_state: HeldShipState,
        layout: BoardLayout,
        x: float,
        y: float,
    ) -> PlacementActionResult:
        board_cell = PlacementEditorService.to_board_cell(layout, x, y)
        if board_cell is not None:
            for ship_type, placement in placements_by_type.items():
                if placement is not None and board_cell in cells_for_placement(placement):
                    placements_by_type[ship_type] = None
                    held_state = HeldShipState(
                        ship_type=ship_type,
                        orientation=placement.orientation,
                        previous=placement,
                        grab_index=grab_index_from_cell(placement, board_cell),
                    )
                    return PlacementActionResult(
                        handled=True,
                        held_state=held_state,
                        status=f"Holding {ship_type.value}. Press R to rotate.",
                        refresh_buttons=True,
                    )

        palette_ship = PlacementEditorService.palette_ship_at_point(ship_order, x, y)
        if palette_ship is not None:
            if placements_by_type.get(palette_ship) is not None:
                return PlacementActionResult(
                    handled=True,
                    held_state=held_state,
                    status=f"{palette_ship.value} is already placed.",
                )
            return PlacementActionResult(
                handled=True,
                held_state=HeldShipState(
                    ship_type=palette_ship,
                    orientation=Orientation.HORIZONTAL,
                    previous=None,
                    grab_index=max(0, palette_ship.size // 2),
                ),
                status=f"Holding {palette_ship.value}. Press R to rotate.",
            )
        return PlacementActionResult(
            handled=False,
            held_state=HeldShipState(ship_type=None, orientation=None, previous=None, grab_index=0),
        )



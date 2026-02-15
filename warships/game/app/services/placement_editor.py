"""Placement editor service helpers."""

from __future__ import annotations

from warships.game.core.board import BoardState
from warships.game.core.models import Coord, ShipPlacement, ShipType
from engine.ui_runtime.board_layout import BoardLayout
from warships.game.ui.layout_metrics import PLACEMENT_PANEL


class PlacementEditorService:
    """Pure helpers for placement editor state transitions."""

    @staticmethod
    def reset(ship_order: list[ShipType]) -> dict[ShipType, ShipPlacement | None]:
        return {ship_type: None for ship_type in ship_order}

    @staticmethod
    def placements_list(placements_by_type: dict[ShipType, ShipPlacement | None]) -> list[ShipPlacement]:
        return [placement for placement in placements_by_type.values() if placement is not None]

    @staticmethod
    def all_ships_placed(
        placements_by_type: dict[ShipType, ShipPlacement | None],
        ship_order: list[ShipType],
    ) -> bool:
        return all(placements_by_type[ship_type] is not None for ship_type in ship_order)

    @staticmethod
    def can_place(
        placements_by_type: dict[ShipType, ShipPlacement | None],
        candidate: ShipPlacement,
    ) -> bool:
        board = BoardState()
        temp: list[ShipPlacement] = [p for p in placements_by_type.values() if p is not None]
        temp.append(candidate)
        seen: set[ShipType] = set()
        for idx, placement in enumerate(temp, start=1):
            if placement.ship_type in seen:
                return False
            seen.add(placement.ship_type)
            if not board.can_place(placement):
                return False
            board.place_ship(idx, placement)
        return True

    @staticmethod
    def to_board_cell(layout: BoardLayout, x: float, y: float) -> Coord | None:
        return layout.screen_to_cell(is_ai=False, px=x, py=y)

    @staticmethod
    def palette_ship_at_point(ship_order: list[ShipType], x: float, y: float) -> ShipType | None:
        panel = PLACEMENT_PANEL.panel_rect()
        if not panel.contains(x, y):
            return None
        for index, ship_type in enumerate(ship_order):
            row = PLACEMENT_PANEL.row_rect(index)
            if row.contains(x, y):
                return ship_type
        return None



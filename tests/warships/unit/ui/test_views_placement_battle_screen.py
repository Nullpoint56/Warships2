from engine.ui_runtime.grid_layout import GridLayout
from warships.game.core.board import BoardState
from warships.game.core.models import Coord, Orientation, ShipPlacement, ShipType
from warships.game.ui.views.placement_battle_screen import (
    draw_ai_board,
    draw_board_frame,
    draw_held_ship_preview,
    draw_placement_panel,
    draw_player_board,
    draw_ships_from_placements,
)

from tests.warships.unit.ui.helpers import FakeRenderer


def test_draw_board_and_placement_panel() -> None:
    renderer = FakeRenderer()
    draw_placement_panel(renderer, [], [ShipType.CARRIER, ShipType.DESTROYER])
    draw_board_frame(renderer, GridLayout(), is_ai=False)
    draw_board_frame(renderer, GridLayout(), is_ai=True)
    assert renderer.rects
    assert renderer.grids


def test_draw_player_and_ai_board_paths() -> None:
    renderer = FakeRenderer()
    layout = GridLayout()
    placements = [ShipPlacement(ShipType.DESTROYER, Coord(0, 0), Orientation.HORIZONTAL)]
    draw_player_board(
        renderer=renderer,
        layout=layout,
        placements=placements,
        session=None,
        held_ship_type=None,
        held_orientation=None,
        held_grab_index=0,
        hover_cell=None,
        hover_x=None,
        hover_y=None,
    )
    draw_ai_board(renderer=renderer, layout=layout, session=None)
    assert renderer.rects


def test_draw_ships_and_held_preview() -> None:
    renderer = FakeRenderer()
    layout = GridLayout()
    placements = [ShipPlacement(ShipType.DESTROYER, Coord(0, 0), Orientation.HORIZONTAL)]
    draw_ships_from_placements(renderer, layout, placements)
    draw_held_ship_preview(
        renderer,
        layout,
        ShipType.DESTROYER,
        Orientation.HORIZONTAL,
        grab_index=0,
        hover_cell=Coord(1, 1),
        hover_x=None,
        hover_y=None,
    )
    board = BoardState()
    board.place_ship(1, ShipPlacement(ShipType.DESTROYER, Coord(2, 2), Orientation.HORIZONTAL))
    assert renderer.rects

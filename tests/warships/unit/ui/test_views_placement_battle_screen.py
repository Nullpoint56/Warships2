from engine.ui_runtime.grid_layout import GridLayout
from tests.warships.unit.ui.helpers import FakeRenderer
from warships.game.core.board import BoardState
from warships.game.core.models import Coord, Orientation, ShipPlacement, ShipType
from warships.game.ui.views.placement_battle_screen import (
    draw_ai_board,
    draw_board_frame,
    draw_held_ship_preview,
    draw_placement_rule_popup,
    draw_placement_panel,
    draw_player_board,
    draw_shots,
    draw_sunk_ship_overlays,
    draw_forbidden_neighbor_cells,
    draw_ships_from_placements,
)


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


def test_draw_player_board_forbidden_overlay_only_while_holding() -> None:
    layout = GridLayout()
    placements = [ShipPlacement(ShipType.DESTROYER, Coord(3, 3), Orientation.HORIZONTAL)]

    idle_renderer = FakeRenderer()
    draw_player_board(
        renderer=idle_renderer,
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
    idle_keys = [str(args[0]) for args, _kwargs in idle_renderer.rects if args]
    assert not any(key.startswith("forbidden:bg:") for key in idle_keys)

    drag_renderer = FakeRenderer()
    draw_player_board(
        renderer=drag_renderer,
        layout=layout,
        placements=placements,
        session=None,
        held_ship_type=ShipType.CARRIER,
        held_orientation=Orientation.HORIZONTAL,
        held_grab_index=0,
        hover_cell=Coord(0, 0),
        hover_x=None,
        hover_y=None,
    )
    drag_keys = [str(args[0]) for args, _kwargs in drag_renderer.rects if args]
    assert any(key.startswith("forbidden:bg:") for key in drag_keys)


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


def test_draw_forbidden_cells_and_invalid_held_preview_uses_danger_color() -> None:
    renderer = FakeRenderer()
    layout = GridLayout()
    placements = [ShipPlacement(ShipType.DESTROYER, Coord(4, 4), Orientation.HORIZONTAL)]
    draw_forbidden_neighbor_cells(renderer, layout, placements)
    draw_held_ship_preview(
        renderer,
        layout,
        ShipType.DESTROYER,
        Orientation.HORIZONTAL,
        grab_index=0,
        hover_cell=Coord(4, 3),
        hover_x=None,
        hover_y=None,
        is_valid=False,
    )
    keys = [str(args[0]) for args, _kwargs in renderer.rects if args]
    assert any(key.startswith("forbidden:bg:") for key in keys)
    held_preview_rect = [
        args for args, _kwargs in renderer.rects if args and str(args[0]).startswith("held:preview:")
    ]
    assert held_preview_rect
    assert held_preview_rect[0][5] == "#d14343"


def test_draw_placement_rule_popup_renders_frame_and_text() -> None:
    renderer = FakeRenderer()
    draw_placement_rule_popup(renderer, "Ships cannot touch. Leave a one-cell gap.")
    rect_keys = [str(args[0]) for args, _kwargs in renderer.rects if args]
    popup_text = [
        str(kwargs.get("text"))
        for _args, kwargs in renderer.texts
        if kwargs and kwargs.get("key") == "placement:popup:text"
    ]
    text_keys = [str(kwargs.get("key")) for _args, kwargs in renderer.texts if kwargs]
    assert any(key.startswith("placement:popup:bg") for key in rect_keys)
    assert "placement:popup:text" in text_keys
    assert popup_text and "..." not in popup_text[0]


def test_draw_shots_emits_impact_fx_overlays() -> None:
    renderer = FakeRenderer()
    layout = GridLayout()
    board = BoardState()
    board.shots[1, 1] = 1
    board.shots[2, 3] = 2

    draw_shots(renderer, layout, board, is_ai=False)

    keys = [args[0] for args, _kwargs in renderer.rects if args]
    assert any(str(key).startswith("shotfx:halo:player:1:1") for key in keys)
    assert any(str(key).startswith("shotfx:core:player:2:3") for key in keys)
    assert any(str(key).startswith("shotfx:ray:h:player:2:3") for key in keys)
    assert any(str(key).startswith("shotfx:ray:v:player:2:3") for key in keys)


def test_draw_sunk_ship_overlays_emits_center_line_for_sunk_ship() -> None:
    renderer = FakeRenderer()
    layout = GridLayout()
    board = BoardState()
    board.place_ship(1, ShipPlacement(ShipType.DESTROYER, Coord(2, 2), Orientation.HORIZONTAL))
    board.apply_shot(Coord(2, 2))
    board.apply_shot(Coord(2, 3))

    draw_sunk_ship_overlays(renderer, layout, board, is_ai=False)

    keys = [str(args[0]) for args, _kwargs in renderer.rects if args]
    assert any(key.startswith("sunkline:outline:player:1") for key in keys)
    assert any(key.startswith("sunkline:fill:player:1") for key in keys)

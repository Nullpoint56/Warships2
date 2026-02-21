"""Rendering helpers for placement and battle boards."""

from __future__ import annotations

from engine.api.render import RenderAPI as Render2D
from engine.api.ui_primitives import GridLayout
from engine.api.ui_style import (
    DEFAULT_UI_STYLE_TOKENS,
    draw_rounded_rect,
    draw_stroke_rect,
)
from warships.game.core.board import BoardState
from warships.game.core.models import (
    Coord,
    Orientation,
    ShipPlacement,
    ShipType,
    cells_for_placement,
)
from warships.game.core.rules import GameSession
from warships.game.ui.layout_metrics import PLACEMENT_PANEL

TOKENS = DEFAULT_UI_STYLE_TOKENS


def draw_placement_panel(
    renderer: Render2D, placements: list[ShipPlacement], ship_order: list[ShipType]
) -> None:
    panel = PLACEMENT_PANEL.panel_rect()
    panel_x = panel.x
    panel_y = panel.y
    panel_w = panel.w
    panel_h = panel.h
    draw_rounded_rect(
        renderer,
        key="placement:panel",
        x=panel_x,
        y=panel_y,
        w=panel_w,
        h=panel_h,
        radius=8.0,
        color=TOKENS.surface_base,
        z=1.0,
    )
    draw_stroke_rect(
        renderer,
        key="placement:panel:border",
        x=panel_x,
        y=panel_y,
        w=panel_w,
        h=panel_h,
        color=TOKENS.border_subtle,
        z=1.01,
    )
    renderer.add_text(
        key="placement:fleet_title",
        text="Ships",
        x=panel_x + panel_w / 2.0,
        y=panel_y + 18.0,
        font_size=16.0,
        color=TOKENS.text_secondary,
        anchor="top-center",
    )

    placed_types = {placement.ship_type for placement in placements}
    for index, ship_type in enumerate(ship_order):
        row = PLACEMENT_PANEL.row_rect(index)
        is_placed = ship_type in placed_types
        color = TOKENS.success if is_placed else TOKENS.border_subtle
        draw_rounded_rect(
            renderer,
            key=f"placement:shipbg:{ship_type.value}",
            x=row.x,
            y=row.y,
            w=row.w,
            h=row.h,
            radius=5.0,
            color=color,
            z=1.1,
        )
        renderer.add_text(
            key=f"placement:ship:{ship_type.value}",
            text=f"{ship_type.value[:3]} ({ship_type.size})",
            x=panel_x + panel_w / 2.0,
            y=row.y + row.h / 2.0,
            font_size=13.0,
            anchor="middle-center",
            color=TOKENS.text_primary,
        )


def draw_player_board(
    renderer: Render2D,
    layout: GridLayout,
    placements: list[ShipPlacement],
    session: GameSession | None,
    held_ship_type: ShipType | None,
    held_orientation: Orientation | None,
    held_grab_index: int,
    hover_cell: Coord | None,
    hover_x: float | None,
    hover_y: float | None,
) -> None:
    draw_board_frame(renderer, layout, is_ai=False)
    player_board = session.player_board if session else None
    if player_board is not None:
        draw_ships_from_board(renderer, layout, player_board, is_ai=False)
        if session:
            draw_shots(renderer, layout, player_board, is_ai=False)
        return
    draw_ships_from_placements(renderer, layout, placements)
    if held_ship_type is not None and held_orientation is not None:
        draw_held_ship_preview(
            renderer,
            layout,
            held_ship_type,
            held_orientation,
            held_grab_index,
            hover_cell,
            hover_x,
            hover_y,
        )


def draw_ai_board(renderer: Render2D, layout: GridLayout, session: GameSession | None) -> None:
    draw_board_frame(renderer, layout, is_ai=True)
    if session is None:
        return
    draw_shots(renderer, layout, session.ai_board, is_ai=True)


def draw_board_frame(renderer: Render2D, layout: GridLayout, is_ai: bool) -> None:
    board_key = "ai" if is_ai else "player"
    target = "secondary" if is_ai else "primary"
    rect = layout.rect_for_target(target)
    draw_rounded_rect(
        renderer,
        key=f"board:bg:{board_key}",
        x=rect.x,
        y=rect.y,
        w=rect.w,
        h=rect.h,
        radius=6.0,
        color=TOKENS.board_bg,
        z=0.1,
    )
    draw_stroke_rect(
        renderer,
        key=f"board:border:{board_key}",
        x=rect.x,
        y=rect.y,
        w=rect.w,
        h=rect.h,
        color=TOKENS.border_accent,
        z=0.15,
    )
    renderer.add_grid(
        key=f"board:grid:{board_key}",
        x=rect.x,
        y=rect.y,
        width=rect.w,
        height=rect.h,
        lines=11,
        color=TOKENS.board_grid,
        z=0.2,
    )


def draw_ships_from_placements(
    renderer: Render2D, layout: GridLayout, placements: list[ShipPlacement]
) -> None:
    for placement in placements:
        for coord in cells_for_placement(placement):
            cell_rect = layout.cell_rect_for_target("primary", row=coord.row, col=coord.col)
            renderer.add_rect(
                f"ship:placement:{placement.ship_type.value}:{coord.row}:{coord.col}",
                cell_rect.x + 2.0,
                cell_rect.y + 2.0,
                cell_rect.w - 4.0,
                cell_rect.h - 4.0,
                TOKENS.success,
                z=0.3,
            )


def draw_ships_from_board(
    renderer: Render2D, layout: GridLayout, board: BoardState, is_ai: bool
) -> None:
    board_key = "ai" if is_ai else "player"
    target = "secondary" if is_ai else "primary"
    for row in range(board.size):
        for col in range(board.size):
            if int(board.ships[row, col]) == 0:
                continue
            cell_rect = layout.cell_rect_for_target(target, row=row, col=col)
            renderer.add_rect(
                f"ship:{board_key}:{row}:{col}",
                cell_rect.x + 2.0,
                cell_rect.y + 2.0,
                cell_rect.w - 4.0,
                cell_rect.h - 4.0,
                TOKENS.success_muted,
                z=0.3,
            )


def draw_shots(renderer: Render2D, layout: GridLayout, board: BoardState, is_ai: bool) -> None:
    board_key = "ai" if is_ai else "player"
    target = "secondary" if is_ai else "primary"
    for row in range(board.size):
        for col in range(board.size):
            value = int(board.shots[row, col])
            if value == 0:
                continue
            cell_rect = layout.cell_rect_for_target(target, row=row, col=col)
            color = TOKENS.danger if value == 2 else TOKENS.text_primary
            renderer.add_rect(
                f"shot:{board_key}:{row}:{col}",
                cell_rect.x + layout.cell_size * 0.3,
                cell_rect.y + layout.cell_size * 0.3,
                layout.cell_size * 0.4,
                layout.cell_size * 0.4,
                color,
                z=0.4,
            )


def draw_held_ship_preview(
    renderer: Render2D,
    layout: GridLayout,
    ship_type: ShipType,
    orientation: Orientation,
    grab_index: int,
    hover_cell: Coord | None,
    hover_x: float | None,
    hover_y: float | None,
) -> None:
    if hover_cell is not None:
        bow_row = hover_cell.row - (grab_index if orientation is Orientation.VERTICAL else 0)
        bow_col = hover_cell.col - (grab_index if orientation is Orientation.HORIZONTAL else 0)
        for i in range(ship_type.size):
            row = bow_row + (i if orientation is Orientation.VERTICAL else 0)
            col = bow_col + (i if orientation is Orientation.HORIZONTAL else 0)
            if row < 0 or row >= 10 or col < 0 or col >= 10:
                continue
            cell_rect = layout.cell_rect_for_target("primary", row=row, col=col)
            renderer.add_rect(
                f"held:preview:{ship_type.value}:{i}",
                cell_rect.x + 2.0,
                cell_rect.y + 2.0,
                cell_rect.w - 4.0,
                cell_rect.h - 4.0,
                TOKENS.warning,
                z=0.35,
            )
        return
    if hover_x is None or hover_y is None:
        return
    for i in range(ship_type.size):
        dx = (i - grab_index) * 22.0 if orientation is Orientation.HORIZONTAL else 0.0
        dy = (i - grab_index) * 22.0 if orientation is Orientation.VERTICAL else 0.0
        renderer.add_rect(
            f"held:preview:float:{ship_type.value}:{i}",
            hover_x + dx - 9.0,
            hover_y + dy - 9.0,
            18.0,
            18.0,
            TOKENS.warning,
            z=1.2,
        )

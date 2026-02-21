"""Rendering helpers for placement and battle boards."""

from __future__ import annotations

from engine.api.render import RenderAPI as Render2D
from engine.api.ui_primitives import GridLayout, Rect, fit_text_to_rect
from engine.api.ui_style import (
    DEFAULT_UI_STYLE_TOKENS,
    draw_rounded_rect,
    draw_stroke_rect,
)
from warships.game.app.state_machine import AppState
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
from warships.game.ui.scene_theme import SceneTheme, theme_for_state

TOKENS = DEFAULT_UI_STYLE_TOKENS


def draw_placement_panel(
    renderer: Render2D,
    placements: list[ShipPlacement],
    ship_order: list[ShipType],
    theme: SceneTheme | None = None,
) -> None:
    active_theme = theme or theme_for_state(AppState.PLACEMENT_EDIT)
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
        color=active_theme.panel_bg,
        z=1.0,
    )
    draw_stroke_rect(
        renderer,
        key="placement:panel:border",
        x=panel_x,
        y=panel_y,
        w=panel_w,
        h=panel_h,
        color=active_theme.panel_border,
        z=1.01,
    )
    title_text, title_font_size = fit_text_to_rect(
        "Ships",
        rect_w=panel_w - 12.0,
        rect_h=24.0,
        base_font_size=16.0,
        min_font_size=11.0,
        pad_x=4.0,
        pad_y=1.0,
        overflow_policy="ellipsis",
    )
    renderer.add_text(
        key="placement:fleet_title",
        text=title_text,
        x=panel_x + panel_w / 2.0,
        y=panel_y + 18.0,
        font_size=title_font_size,
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
        ship_label, ship_font_size = fit_text_to_rect(
            f"{ship_type.value[:3]} ({ship_type.size})",
            rect_w=row.w - 8.0,
            rect_h=row.h - 4.0,
            base_font_size=13.0,
            min_font_size=10.0,
            pad_x=3.0,
            pad_y=1.0,
            overflow_policy="ellipsis",
        )
        renderer.add_text(
            key=f"placement:ship:{ship_type.value}",
            text=ship_label,
            x=panel_x + panel_w / 2.0,
            y=row.y + row.h / 2.0,
            font_size=ship_font_size,
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
    theme: SceneTheme | None = None,
) -> None:
    draw_board_frame(renderer, layout, is_ai=False, theme=theme)
    player_board = session.player_board if session else None
    if player_board is not None:
        draw_ships_from_board(renderer, layout, player_board, is_ai=False)
        if session:
            draw_shots(renderer, layout, player_board, is_ai=False)
            draw_sunk_ship_overlays(renderer, layout, player_board, is_ai=False)
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


def draw_ai_board(
    renderer: Render2D,
    layout: GridLayout,
    session: GameSession | None,
    theme: SceneTheme | None = None,
) -> None:
    draw_board_frame(renderer, layout, is_ai=True, theme=theme)
    if session is None:
        return
    draw_shots(renderer, layout, session.ai_board, is_ai=True)
    draw_sunk_ship_overlays(renderer, layout, session.ai_board, is_ai=True)


def draw_board_frame(
    renderer: Render2D, layout: GridLayout, is_ai: bool, theme: SceneTheme | None = None
) -> None:
    active_theme = theme or theme_for_state(AppState.PLACEMENT_EDIT)
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
        color=active_theme.board_bg,
        z=0.1,
    )
    draw_stroke_rect(
        renderer,
        key=f"board:border:{board_key}",
        x=rect.x,
        y=rect.y,
        w=rect.w,
        h=rect.h,
        color=active_theme.board_border,
        z=0.15,
    )
    renderer.add_grid(
        key=f"board:grid:{board_key}",
        x=rect.x,
        y=rect.y,
        width=rect.w,
        height=rect.h,
        lines=11,
        color=active_theme.board_grid,
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
            _draw_shot_impact_fx(
                renderer=renderer,
                board_key=board_key,
                row=row,
                col=col,
                cell_rect=cell_rect,
                value=value,
            )


def draw_sunk_ship_overlays(
    renderer: Render2D, layout: GridLayout, board: BoardState, is_ai: bool
) -> None:
    board_key = "ai" if is_ai else "player"
    target = "secondary" if is_ai else "primary"
    for ship_id, remaining in board.ship_remaining.items():
        if int(remaining) != 0:
            continue
        cells = board.ship_cells.get(int(ship_id), [])
        if not cells:
            continue
        rows = [int(cell.row) for cell in cells]
        cols = [int(cell.col) for cell in cells]
        min_row = min(rows)
        max_row = max(rows)
        min_col = min(cols)
        max_col = max(cols)
        first = layout.cell_rect_for_target(target, row=min_row, col=min_col)
        last = layout.cell_rect_for_target(target, row=max_row, col=max_col)
        is_horizontal = min_row == max_row
        outline = max(2.0, layout.cell_size * 0.14)
        fill = max(1.0, layout.cell_size * 0.08)
        if is_horizontal:
            x = first.x + 2.0
            y = first.y + (first.h * 0.5)
            w = (last.x + last.w - 2.0) - x
            renderer.add_rect(
                f"sunkline:outline:{board_key}:{ship_id}",
                x,
                y - (outline * 0.5),
                max(1.0, w),
                outline,
                TOKENS.shadow_strong,
                z=0.48,
            )
            renderer.add_rect(
                f"sunkline:fill:{board_key}:{ship_id}",
                x,
                y - (fill * 0.5),
                max(1.0, w),
                fill,
                TOKENS.warning,
                z=0.49,
            )
            continue
        x = first.x + (first.w * 0.5)
        y = first.y + 2.0
        h = (last.y + last.h - 2.0) - y
        renderer.add_rect(
            f"sunkline:outline:{board_key}:{ship_id}",
            x - (outline * 0.5),
            y,
            outline,
            max(1.0, h),
            TOKENS.shadow_strong,
            z=0.48,
        )
        renderer.add_rect(
            f"sunkline:fill:{board_key}:{ship_id}",
            x - (fill * 0.5),
            y,
            fill,
            max(1.0, h),
            TOKENS.warning,
            z=0.49,
        )


def _draw_shot_impact_fx(
    *,
    renderer: Render2D,
    board_key: str,
    row: int,
    col: int,
    cell_rect: Rect,
    value: int,
) -> None:
    x = float(getattr(cell_rect, "x", 0.0))
    y = float(getattr(cell_rect, "y", 0.0))
    w = float(getattr(cell_rect, "w", 1.0))
    h = float(getattr(cell_rect, "h", 1.0))
    cx = x + (w * 0.5)
    cy = y + (h * 0.5)
    if value == 2:
        core = TOKENS.danger
        halo = "#ff6b6b55"
        spark = "#ffd7d788"
    else:
        core = TOKENS.text_primary
        halo = "#c7d5ec33"
        spark = "#dbeafe66"
    renderer.add_rect(
        f"shotfx:halo:{board_key}:{row}:{col}",
        cx - (w * 0.25),
        cy - (h * 0.25),
        w * 0.5,
        h * 0.5,
        halo,
        z=0.38,
    )
    ray_t = max(1.0, w * 0.06)
    ray_l = w * 0.18
    renderer.add_rect(
        f"shotfx:ray:h:{board_key}:{row}:{col}",
        cx - ray_l,
        cy - (ray_t * 0.5),
        ray_l * 2.0,
        ray_t,
        spark,
        z=0.41,
    )
    renderer.add_rect(
        f"shotfx:ray:v:{board_key}:{row}:{col}",
        cx - (ray_t * 0.5),
        cy - ray_l,
        ray_t,
        ray_l * 2.0,
        spark,
        z=0.41,
    )
    renderer.add_rect(
        f"shotfx:core:{board_key}:{row}:{col}",
        cx - (w * 0.08),
        cy - (h * 0.08),
        w * 0.16,
        h * 0.16,
        core,
        z=0.42,
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

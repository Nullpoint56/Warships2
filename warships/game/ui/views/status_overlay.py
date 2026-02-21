"""Status bar and board title overlay rendering."""

from __future__ import annotations

from engine.api.render import RenderAPI as Render2D
from engine.api.ui_primitives import fit_text_to_rect
from engine.api.ui_style import DEFAULT_UI_STYLE_TOKENS, draw_rounded_rect, draw_stroke_rect
from warships.game.app.state_machine import AppState
from warships.game.core.models import Orientation, ShipPlacement, ShipType
from warships.game.ui.scene_theme import SceneTheme, theme_for_state
from warships.game.ui.layout_metrics import status_rect

TOKENS = DEFAULT_UI_STYLE_TOKENS


def draw_status_bar(
    renderer: Render2D,
    state: AppState,
    status: str,
    placement_orientation: Orientation,
    placements: list[ShipPlacement],
    ship_order: list[ShipType],
    theme: SceneTheme | None = None,
) -> None:
    if state is AppState.MAIN_MENU:
        return
    active_theme = theme or theme_for_state(state)
    status_box = status_rect()
    status_lower = str(status).strip().lower()
    sink_alert = "sunk" in status_lower
    border_color = TOKENS.warning if sink_alert else active_theme.status_border
    draw_rounded_rect(
        renderer,
        key="status:bg",
        x=status_box.x,
        y=status_box.y,
        w=status_box.w,
        h=status_box.h,
        radius=6.0,
        color=active_theme.status_bg,
        z=1.0,
    )
    draw_stroke_rect(
        renderer,
        key="status:border",
        x=status_box.x,
        y=status_box.y,
        w=status_box.w,
        h=status_box.h,
        color=border_color,
        z=1.01,
        thickness=2.0 if sink_alert else 1.0,
    )
    if sink_alert:
        draw_rounded_rect(
            renderer,
            key="status:alert:bg",
            x=status_box.x + status_box.w - 220.0,
            y=status_box.y + 6.0,
            w=200.0,
            h=18.0,
            radius=4.0,
            color="#7a4e00",
            z=1.02,
        )
        renderer.add_text(
            key="status:alert",
            text="SHIP SUNK!",
            x=status_box.x + status_box.w - 120.0,
            y=status_box.y + 15.0,
            font_size=12.0,
            color=TOKENS.warning,
            anchor="middle-center",
            z=3.2,
        )
    show_placement_hint = state is AppState.PLACEMENT_EDIT and len(placements) < len(ship_order)
    status_text_value = status
    if show_placement_hint:
        status_text_value = (
            "Drag and drop ships. Hold a ship and press R to rotate. "
            f"Orientation: {placement_orientation.value}"
        )
    status_text, status_font_size = fit_text_to_rect(
        status_text_value,
        rect_w=status_box.w - 28.0,
        rect_h=status_box.h - 6.0,
        base_font_size=16.0,
        min_font_size=11.0,
        pad_x=4.0,
        pad_y=1.0,
        overflow_policy="ellipsis",
    )
    renderer.add_text(
        key="status:main",
        text=status_text,
        x=status_box.x + 14.0,
        y=status_box.y + status_box.h / 2.0,
        font_size=status_font_size,
        color=TOKENS.text_secondary,
        anchor="middle-left",
    )
    if state in (AppState.PLACEMENT_EDIT, AppState.BATTLE, AppState.RESULT):
        player_title, player_title_size = fit_text_to_rect(
            "Player Board",
            rect_w=220.0,
            rect_h=26.0,
            base_font_size=20.0,
            min_font_size=12.0,
            pad_x=2.0,
            pad_y=1.0,
            overflow_policy="ellipsis",
        )
        renderer.add_text(
            key="title:player",
            text=player_title,
            x=80.0,
            y=132.0,
            font_size=player_title_size,
            color=TOKENS.text_muted,
            anchor="bottom-left",
        )
    if state in (AppState.BATTLE, AppState.RESULT):
        enemy_title, enemy_title_size = fit_text_to_rect(
            "Enemy Board",
            rect_w=220.0,
            rect_h=26.0,
            base_font_size=20.0,
            min_font_size=12.0,
            pad_x=2.0,
            pad_y=1.0,
            overflow_policy="ellipsis",
        )
        renderer.add_text(
            key="title:enemy",
            text=enemy_title,
            x=640.0,
            y=132.0,
            font_size=enemy_title_size,
            color=TOKENS.text_muted,
            anchor="bottom-left",
        )
    # Placement hint is merged into status:main to avoid redundant duplicate lines.

"""Status bar and board title overlay rendering."""

from __future__ import annotations

from engine.api.render import RenderAPI as Render2D
from engine.api.ui_style import DEFAULT_UI_STYLE_TOKENS, draw_rounded_rect, draw_stroke_rect
from warships.game.app.state_machine import AppState
from warships.game.core.models import Orientation, ShipPlacement, ShipType
from warships.game.ui.layout_metrics import status_rect

TOKENS = DEFAULT_UI_STYLE_TOKENS


def draw_status_bar(
    renderer: Render2D,
    state: AppState,
    status: str,
    placement_orientation: Orientation,
    placements: list[ShipPlacement],
    ship_order: list[ShipType],
) -> None:
    if state is AppState.MAIN_MENU:
        return
    status_box = status_rect()
    draw_rounded_rect(
        renderer,
        key="status:bg",
        x=status_box.x,
        y=status_box.y,
        w=status_box.w,
        h=status_box.h,
        radius=6.0,
        color=TOKENS.board_bg,
        z=1.0,
    )
    draw_stroke_rect(
        renderer,
        key="status:border",
        x=status_box.x,
        y=status_box.y,
        w=status_box.w,
        h=status_box.h,
        color=TOKENS.border_accent,
        z=1.01,
    )
    renderer.add_text(
        key="status:main",
        text=status,
        x=status_box.x + 14.0,
        y=status_box.y + status_box.h / 2.0,
        font_size=16.0,
        color=TOKENS.text_secondary,
        anchor="middle-left",
    )
    if state in (AppState.PLACEMENT_EDIT, AppState.BATTLE, AppState.RESULT):
        renderer.add_text(
            key="title:player",
            text="Player Board",
            x=80.0,
            y=132.0,
            font_size=20.0,
            color=TOKENS.text_muted,
            anchor="bottom-left",
        )
    if state in (AppState.BATTLE, AppState.RESULT):
        renderer.add_text(
            key="title:enemy",
            text="Enemy Board",
            x=640.0,
            y=132.0,
            font_size=20.0,
            color=TOKENS.text_muted,
            anchor="bottom-left",
        )
    if state is AppState.PLACEMENT_EDIT and len(placements) < len(ship_order):
        hint_text = (
            "Drag and drop ships. Hold a ship and press R to rotate. "
            f"Orientation: {placement_orientation.value}"
        )
        renderer.add_text(
            key="status:placement_hint",
            text=hint_text,
            x=640.0,
            y=status_box.y + status_box.h / 2.0,
            font_size=15.0,
            color=TOKENS.text_muted,
            anchor="middle-left",
        )

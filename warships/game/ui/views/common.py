"""Shared view rendering helpers."""

from __future__ import annotations

from engine.api.render import RenderAPI as Render2D
from engine.api.ui_style import DEFAULT_UI_STYLE_TOKENS, draw_rounded_rect
from warships.game.core.models import ShipPlacement, cells_for_placement

TOKENS = DEFAULT_UI_STYLE_TOKENS


def draw_preset_preview(
    *,
    renderer: Render2D,
    key_prefix: str,
    placements: list[ShipPlacement],
    x: float,
    y: float,
    cell: float,
) -> None:
    """Render a compact 10x10 fleet preview."""
    draw_rounded_rect(
        renderer,
        key=f"preset:preview:bg:{key_prefix}",
        x=x,
        y=y,
        w=cell * 10,
        h=cell * 10,
        radius=max(2.0, cell),
        color=TOKENS.board_bg,
        z=1.0,
    )
    for placement in placements:
        for coord in cells_for_placement(placement):
            renderer.add_rect(
                f"preset:preview:cell:{key_prefix}:{coord.row}:{coord.col}",
                x + coord.col * cell + 0.5,
                y + coord.row * cell + 0.5,
                cell - 1.0,
                cell - 1.0,
                TOKENS.success,
                z=1.1,
            )


def is_new_game_custom_button(button_id: str) -> bool:
    """Buttons drawn by the custom new-game view instead of generic overlay widgets."""
    return (
        button_id == "new_game_toggle_difficulty"
        or button_id == "new_game_randomize"
        or button_id.startswith("new_game_diff_option:")
        or button_id.startswith("new_game_select_preset:")
    )

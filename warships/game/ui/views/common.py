"""Shared view rendering helpers."""

from __future__ import annotations

from engine.api.render import RenderAPI as Render2D
from warships.game.core.models import ShipPlacement, cells_for_placement


def truncate(text: str, max_len: int) -> str:
    """Truncate text to fit fixed-width UI containers."""
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    return text[: max_len - 3] + "..."


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
    renderer.add_rect(
        f"preset:preview:bg:{key_prefix}", x, y, cell * 10, cell * 10, "#1e3a8a", z=1.0
    )
    for placement in placements:
        for coord in cells_for_placement(placement):
            renderer.add_rect(
                f"preset:preview:cell:{key_prefix}:{coord.row}:{coord.col}",
                x + coord.col * cell + 0.5,
                y + coord.row * cell + 0.5,
                cell - 1.0,
                cell - 1.0,
                "#10b981",
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

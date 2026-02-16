"""Rendering for preset manager screen."""

from __future__ import annotations

from warships.game.app.ui_state import AppUIState
from warships.game.ui.layout_metrics import PRESET_PANEL
from warships.game.ui.views.common import draw_preset_preview, truncate


def draw_preset_manage(renderer, ui: AppUIState) -> None:
    panel = PRESET_PANEL.panel_rect()
    panel_x = panel.x
    panel_y = panel.y
    panel_w = panel.w
    panel_h = panel.h
    renderer.add_rect("presets:panel", panel_x, panel_y, panel_w, panel_h, "#0f172a", z=0.85)
    renderer.add_text(
        key="presets:title",
        text="Preset Manager",
        x=panel_x + 16.0,
        y=panel_y + 16.0,
        font_size=28.0,
        color="#dbeafe",
        anchor="top-left",
    )
    for idx, row in enumerate(ui.preset_rows):
        row_rect = PRESET_PANEL.row_rect(idx)
        renderer.add_rect(
            f"preset:row:{row.name}",
            row_rect.x,
            row_rect.y,
            row_rect.w,
            row_rect.h,
            "#111827",
            z=0.9,
        )
        renderer.add_text(
            key=f"preset:name:{row.name}",
            text=truncate(row.name, PRESET_PANEL.name_max_len),
            x=row_rect.x + PRESET_PANEL.name_x_pad,
            y=row_rect.y + PRESET_PANEL.name_y_pad,
            font_size=18.0,
            color="#e5e7eb",
            anchor="top-left",
        )
        preview = PRESET_PANEL.preview_rect(idx)
        draw_preset_preview(
            renderer=renderer,
            key_prefix=row.name,
            placements=row.placements,
            x=preview.x,
            y=preview.y,
            cell=PRESET_PANEL.preview_cell,
        )
        edit_rect, rename_rect, delete_rect = PRESET_PANEL.action_button_rects(idx)
        renderer.add_rect(
            f"preset:btnbg:edit:{row.name}",
            edit_rect.x,
            edit_rect.y,
            edit_rect.w,
            edit_rect.h,
            "#1f6feb",
            z=1.0,
        )
        renderer.add_rect(
            f"preset:btnbg:rename:{row.name}",
            rename_rect.x,
            rename_rect.y,
            rename_rect.w,
            rename_rect.h,
            "#1f6feb",
            z=1.0,
        )
        renderer.add_rect(
            f"preset:btnbg:delete:{row.name}",
            delete_rect.x,
            delete_rect.y,
            delete_rect.w,
            delete_rect.h,
            "#b91c1c",
            z=1.0,
        )
    if ui.preset_manage_can_scroll_up:
        renderer.add_text(
            key="presets:scroll:up",
            text="^ more",
            x=panel_x + panel_w - 78.0,
            y=panel_y + 28.0,
            font_size=14.0,
            color="#93c5fd",
            anchor="middle-left",
            z=1.05,
        )
    if ui.preset_manage_can_scroll_down:
        renderer.add_text(
            key="presets:scroll:down",
            text="v more",
            x=panel_x + panel_w - 78.0,
            y=panel_y + panel_h - 14.0,
            font_size=14.0,
            color="#93c5fd",
            anchor="middle-left",
            z=1.05,
        )

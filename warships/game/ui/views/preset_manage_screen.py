"""Rendering for preset manager screen."""

from __future__ import annotations

from engine.api.render import RenderAPI as Render2D
from engine.api.ui_style import (
    DEFAULT_UI_STYLE_TOKENS,
    draw_rounded_rect,
    draw_shadow_rect,
    draw_stroke_rect,
)
from warships.game.app.ui_state import AppUIState
from warships.game.ui.layout_metrics import PRESET_PANEL
from warships.game.ui.views.common import draw_preset_preview, truncate

TOKENS = DEFAULT_UI_STYLE_TOKENS


def draw_preset_manage(renderer: Render2D, ui: AppUIState) -> None:
    panel = PRESET_PANEL.panel_rect()
    panel_x = panel.x
    panel_y = panel.y
    panel_w = panel.w
    panel_h = panel.h
    draw_shadow_rect(
        renderer,
        key="presets:panel:shadow",
        x=panel_x + 2.0,
        y=panel_y + 2.0,
        w=panel_w,
        h=panel_h,
        color=TOKENS.shadow_strong,
        z=0.82,
    )
    draw_rounded_rect(
        renderer,
        key="presets:panel",
        x=panel_x,
        y=panel_y,
        w=panel_w,
        h=panel_h,
        radius=10.0,
        color=TOKENS.surface_base,
        z=0.85,
    )
    draw_stroke_rect(
        renderer,
        key="presets:panel:border",
        x=panel_x,
        y=panel_y,
        w=panel_w,
        h=panel_h,
        color=TOKENS.border_subtle,
        z=0.86,
    )
    renderer.add_text(
        key="presets:title",
        text="Preset Manager",
        x=panel_x + 16.0,
        y=panel_y + 16.0,
        font_size=28.0,
        color=TOKENS.text_secondary,
        anchor="top-left",
    )
    for idx, row in enumerate(ui.preset_rows):
        row_rect = PRESET_PANEL.row_rect(idx)
        draw_rounded_rect(
            renderer,
            key=f"preset:row:{row.name}",
            x=row_rect.x,
            y=row_rect.y,
            w=row_rect.w,
            h=row_rect.h,
            radius=8.0,
            color=TOKENS.surface_overlay,
            z=0.9,
        )
        draw_stroke_rect(
            renderer,
            key=f"preset:row:border:{row.name}",
            x=row_rect.x,
            y=row_rect.y,
            w=row_rect.w,
            h=row_rect.h,
            color=TOKENS.border_subtle,
            z=0.91,
        )
        renderer.add_text(
            key=f"preset:name:{row.name}",
            text=truncate(row.name, PRESET_PANEL.name_max_len),
            x=row_rect.x + PRESET_PANEL.name_x_pad,
            y=row_rect.y + PRESET_PANEL.name_y_pad,
            font_size=18.0,
            color=TOKENS.text_primary,
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
        draw_rounded_rect(
            renderer,
            key=f"preset:btnbg:edit:{row.name}",
            x=edit_rect.x,
            y=edit_rect.y,
            w=edit_rect.w,
            h=edit_rect.h,
            radius=5.0,
            color=TOKENS.accent,
            z=1.0,
        )
        draw_rounded_rect(
            renderer,
            key=f"preset:btnbg:rename:{row.name}",
            x=rename_rect.x,
            y=rename_rect.y,
            w=rename_rect.w,
            h=rename_rect.h,
            radius=5.0,
            color=TOKENS.accent,
            z=1.0,
        )
        draw_rounded_rect(
            renderer,
            key=f"preset:btnbg:delete:{row.name}",
            x=delete_rect.x,
            y=delete_rect.y,
            w=delete_rect.w,
            h=delete_rect.h,
            radius=5.0,
            color=TOKENS.danger,
            z=1.0,
        )
    if ui.preset_manage_can_scroll_up:
        renderer.add_text(
            key="presets:scroll:up",
            text="^ more",
            x=panel_x + panel_w - 78.0,
            y=panel_y + 28.0,
            font_size=14.0,
            color=TOKENS.text_muted,
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
            color=TOKENS.text_muted,
            anchor="middle-left",
            z=1.05,
        )

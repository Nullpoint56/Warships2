"""Rendering for preset manager screen."""

from __future__ import annotations

from engine.api.render import RenderAPI as Render2D
from engine.api.ui_primitives import Rect, fit_text_to_rect
from engine.api.ui_projection import TextFitSpec, project_text_fit
from engine.api.ui_style import (
    DEFAULT_UI_STYLE_TOKENS,
    draw_rounded_rect,
    draw_shadow_rect,
    draw_stroke_rect,
)
from warships.game.app.ui_state import AppUIState
from warships.game.ui.layout_metrics import PRESET_PANEL
from warships.game.ui.views.common import draw_preset_preview

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
    title_text, title_font_size = fit_text_to_rect(
        "Preset Manager",
        rect_w=panel_w - 32.0,
        rect_h=34.0,
        base_font_size=28.0,
        min_font_size=16.0,
        overflow_policy="ellipsis",
    )
    renderer.add_text(
        key="presets:title",
        text=title_text,
        x=panel_x + 16.0,
        y=panel_y + 16.0,
        font_size=title_font_size,
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
        name_text, name_font_size, _ = project_text_fit(
            TextFitSpec(
                text=row.name,
                rect=Rect(
                    row_rect.x + PRESET_PANEL.name_x_pad,
                    row_rect.y + PRESET_PANEL.name_y_pad,
                    row_rect.w - (PRESET_PANEL.name_x_pad + 8.0),
                    28.0,
                ),
                base_font_size=18.0,
                min_font_size=12.0,
                pad_x=4.0,
                pad_y=0.0,
                overflow_policy="ellipsis",
                parent=row_rect,
                enforce_parent=True,
            )
        )
        renderer.add_text(
            key=f"preset:name:{row.name}",
            text=name_text,
            x=row_rect.x + PRESET_PANEL.name_x_pad,
            y=row_rect.y + PRESET_PANEL.name_y_pad,
            font_size=name_font_size,
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
        scroll_up_text, scroll_up_size = fit_text_to_rect(
            "^ more",
            rect_w=70.0,
            rect_h=18.0,
            base_font_size=14.0,
            min_font_size=10.0,
            overflow_policy="ellipsis",
        )
        renderer.add_text(
            key="presets:scroll:up",
            text=scroll_up_text,
            x=panel_x + panel_w - 78.0,
            y=panel_y + 28.0,
            font_size=scroll_up_size,
            color=TOKENS.text_muted,
            anchor="middle-left",
            z=1.05,
        )
    if ui.preset_manage_can_scroll_down:
        scroll_down_text, scroll_down_size = fit_text_to_rect(
            "v more",
            rect_w=70.0,
            rect_h=18.0,
            base_font_size=14.0,
            min_font_size=10.0,
            overflow_policy="ellipsis",
        )
        renderer.add_text(
            key="presets:scroll:down",
            text=scroll_down_text,
            x=panel_x + panel_w - 78.0,
            y=panel_y + panel_h - 14.0,
            font_size=scroll_down_size,
            color=TOKENS.text_muted,
            anchor="middle-left",
            z=1.05,
        )

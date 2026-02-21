"""Rendering for new-game setup screen."""

from __future__ import annotations

from engine.api.render import RenderAPI as Render2D
from engine.api.ui_primitives import fit_text_to_rect
from engine.api.ui_style import (
    DEFAULT_UI_STYLE_TOKENS,
    draw_rounded_rect,
    draw_shadow_rect,
    draw_stroke_rect,
)
from warships.game.app.ui_state import AppUIState
from warships.game.ui.layout_metrics import NEW_GAME_SETUP
from warships.game.ui.views.common import draw_preset_preview, truncate

TOKENS = DEFAULT_UI_STYLE_TOKENS


def draw_new_game_setup(renderer: Render2D, ui: AppUIState) -> None:
    panel = NEW_GAME_SETUP.panel_rect()
    draw_shadow_rect(
        renderer,
        key="newgame:panel:shadow",
        x=panel.x + 2.0,
        y=panel.y + 2.0,
        w=panel.w,
        h=panel.h,
        color=TOKENS.shadow_strong,
        z=0.82,
    )
    draw_rounded_rect(
        renderer,
        key="newgame:panel",
        x=panel.x,
        y=panel.y,
        w=panel.w,
        h=panel.h,
        radius=10.0,
        color=TOKENS.surface_base,
        z=0.85,
    )
    draw_stroke_rect(
        renderer,
        key="newgame:panel:border",
        x=panel.x,
        y=panel.y,
        w=panel.w,
        h=panel.h,
        color=TOKENS.border_subtle,
        z=0.86,
    )
    renderer.add_text(
        key="newgame:title",
        text="New Game Setup",
        x=panel.x + 20.0,
        y=panel.y + 20.0,
        font_size=30.0,
        color=TOKENS.text_secondary,
        anchor="top-left",
    )
    renderer.add_text(
        key="newgame:difficulty_label",
        text="Difficulty",
        x=panel.x + 20.0,
        y=panel.y + NEW_GAME_SETUP.difficulty_label_y,
        font_size=16.0,
        color=TOKENS.text_muted,
        anchor="top-left",
    )
    diff_rect = NEW_GAME_SETUP.difficulty_rect()
    draw_rounded_rect(
        renderer,
        key="newgame:diff:bg",
        x=diff_rect.x,
        y=diff_rect.y,
        w=diff_rect.w,
        h=diff_rect.h,
        radius=6.0,
        color=TOKENS.surface_elevated,
        z=0.9,
    )
    draw_stroke_rect(
        renderer,
        key="newgame:diff:border",
        x=diff_rect.x,
        y=diff_rect.y,
        w=diff_rect.w,
        h=diff_rect.h,
        color=TOKENS.border_subtle,
        z=0.91,
    )
    renderer.add_text(
        key="newgame:difficulty",
        text=ui.new_game_difficulty or "Normal",
        x=diff_rect.x + 12.0,
        y=diff_rect.y + diff_rect.h / 2.0,
        font_size=20.0,
        color=TOKENS.text_primary,
        anchor="middle-left",
    )
    if ui.new_game_difficulty_open:
        for idx, name in enumerate(ui.new_game_difficulty_options):
            option = NEW_GAME_SETUP.difficulty_option_rect(idx)
            color = TOKENS.accent_hover if name == ui.new_game_difficulty else TOKENS.border_subtle
            draw_rounded_rect(
                renderer,
                key=f"newgame:diff:opt:bg:{name}",
                x=option.x,
                y=option.y,
                w=option.w,
                h=option.h,
                radius=5.0,
                color=color,
                z=0.95,
            )
            option_text, option_font_size = fit_text_to_rect(
                name,
                rect_w=option.w,
                rect_h=option.h,
                base_font_size=16.0,
            )
            renderer.add_text(
                key=f"newgame:diff:opt:text:{name}",
                text=option_text,
                x=option.x + 10.0,
                y=option.y + option.h / 2.0,
                font_size=option_font_size,
                color=TOKENS.text_primary,
                anchor="middle-left",
                z=0.96,
            )

    list_rect = NEW_GAME_SETUP.preset_list_rect()
    draw_rounded_rect(
        renderer,
        key="newgame:presets:bg",
        x=list_rect.x,
        y=list_rect.y,
        w=list_rect.w,
        h=list_rect.h,
        radius=8.0,
        color=TOKENS.surface_overlay,
        z=0.88,
    )
    draw_stroke_rect(
        renderer,
        key="newgame:presets:border",
        x=list_rect.x,
        y=list_rect.y,
        w=list_rect.w,
        h=list_rect.h,
        color=TOKENS.border_subtle,
        z=0.89,
    )
    renderer.add_text(
        key="newgame:presets:title",
        text="Available Presets",
        x=list_rect.x + 12.0,
        y=list_rect.y + 10.0,
        font_size=16.0,
        color=TOKENS.text_muted,
        anchor="top-left",
        z=0.9,
    )
    for idx, name in enumerate(ui.new_game_visible_presets):
        row = NEW_GAME_SETUP.preset_row_rect(idx)
        color = TOKENS.accent_hover if name == ui.new_game_selected_preset else TOKENS.surface_elevated
        draw_rounded_rect(
            renderer,
            key=f"newgame:preset:row:{name}",
            x=row.x,
            y=row.y,
            w=row.w,
            h=row.h,
            radius=6.0,
            color=color,
            z=0.9,
        )
        renderer.add_text(
            key=f"newgame:preset:text:{name}",
            text=truncate(name, 36),
            x=row.x + 12.0,
            y=row.y + row.h / 2.0,
            font_size=16.0,
            color=TOKENS.text_on_accent if name == ui.new_game_selected_preset else TOKENS.text_primary,
            anchor="middle-left",
            z=0.92,
        )
    random_btn = NEW_GAME_SETUP.random_button_rect()
    draw_rounded_rect(
        renderer,
        key="newgame:random:bg",
        x=random_btn.x,
        y=random_btn.y,
        w=random_btn.w,
        h=random_btn.h,
        radius=7.0,
        color=TOKENS.accent,
        z=0.9,
    )
    draw_stroke_rect(
        renderer,
        key="newgame:random:border",
        x=random_btn.x,
        y=random_btn.y,
        w=random_btn.w,
        h=random_btn.h,
        color=TOKENS.border_accent,
        z=0.91,
    )
    random_text, random_font_size = fit_text_to_rect(
        "Generate Random Fleet",
        rect_w=random_btn.w,
        rect_h=random_btn.h,
        base_font_size=14.0,
    )
    renderer.add_text(
        key="newgame:random:text",
        text=random_text,
        x=random_btn.x + random_btn.w / 2.0,
        y=random_btn.y + random_btn.h / 2.0,
        font_size=random_font_size,
        color=TOKENS.text_on_accent,
        anchor="middle-center",
        z=0.92,
    )

    renderer.add_text(
        key="newgame:preview_title",
        text=f"Selected Setup: {ui.new_game_source or 'None'}",
        x=panel.x + NEW_GAME_SETUP.preview_x,
        y=panel.y + NEW_GAME_SETUP.preview_title_y,
        font_size=20.0,
        color=TOKENS.text_muted,
        anchor="top-left",
    )
    preview_x, preview_y = NEW_GAME_SETUP.preview_origin()
    draw_preset_preview(
        renderer=renderer,
        key_prefix="newgame:selected",
        placements=ui.new_game_preview,
        x=preview_x,
        y=preview_y,
        cell=NEW_GAME_SETUP.preview_cell,
    )

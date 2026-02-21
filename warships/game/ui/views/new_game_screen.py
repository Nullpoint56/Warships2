"""Rendering for new-game setup screen."""

from __future__ import annotations

from engine.api.render import RenderAPI as Render2D
from engine.api.ui_primitives import Rect, fit_text_to_rect
from engine.api.ui_projection import TextFitSpec, project_text_fit
from engine.api.ui_style import (
    DEFAULT_UI_STYLE_TOKENS,
    draw_gradient_rect,
    draw_rounded_rect,
    draw_shadow_rect,
    draw_stroke_rect,
)
from warships.game.app.state_machine import AppState
from warships.game.app.ui_state import AppUIState
from warships.game.ui.layout_metrics import NEW_GAME_SETUP
from warships.game.ui.scene_theme import SceneTheme, theme_for_state
from warships.game.ui.views.common import draw_preset_preview

TOKENS = DEFAULT_UI_STYLE_TOKENS


def draw_new_game_setup(
    renderer: Render2D, ui: AppUIState, theme: SceneTheme | None = None
) -> None:
    active_theme = theme or theme_for_state(AppState.NEW_GAME_SETUP)
    panel = NEW_GAME_SETUP.panel_rect()
    draw_shadow_rect(
        renderer,
        key="newgame:panel:shadow",
        x=panel.x + 2.0,
        y=panel.y + 2.0,
        w=panel.w,
        h=panel.h,
        color=TOKENS.shadow_soft,
        corner_radius=10.0,
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
        color=active_theme.panel_bg,
        z=0.85,
    )
    draw_gradient_rect(
        renderer,
        key="newgame:panel:glow",
        x=panel.x + 2.0,
        y=panel.y + 2.0,
        w=max(1.0, panel.w - 4.0),
        h=max(1.0, panel.h * 0.16),
        top_color=active_theme.panel_glow_top,
        bottom_color=TOKENS.highlight_bottom_clear,
        z=0.855,
        steps=4,
    )
    for idx in range(5):
        renderer.add_rect(
            f"newgame:panel:pattern:{idx}",
            panel.x + 18.0 + idx * 36.0,
            panel.y + 16.0,
            20.0,
            2.0,
            active_theme.panel_pattern,
            z=0.856,
        )
    draw_stroke_rect(
        renderer,
        key="newgame:panel:border",
        x=panel.x,
        y=panel.y,
        w=panel.w,
        h=panel.h,
        color=active_theme.panel_border,
        z=0.86,
    )
    title_text, title_font_size = fit_text_to_rect(
        "New Game Setup",
        rect_w=panel.w - 40.0,
        rect_h=36.0,
        base_font_size=30.0,
        min_font_size=16.0,
        pad_x=6.0,
        pad_y=2.0,
        overflow_policy="ellipsis",
    )
    renderer.add_text(
        key="newgame:title",
        text=title_text,
        x=panel.x + 20.0,
        y=panel.y + 20.0,
        font_size=title_font_size,
        color=TOKENS.text_secondary,
        anchor="top-left",
    )
    difficulty_label_text, difficulty_label_size = fit_text_to_rect(
        "Difficulty",
        rect_w=160.0,
        rect_h=22.0,
        base_font_size=16.0,
        min_font_size=10.0,
        pad_x=4.0,
        pad_y=1.0,
        overflow_policy="ellipsis",
    )
    renderer.add_text(
        key="newgame:difficulty_label",
        text=difficulty_label_text,
        x=panel.x + 20.0,
        y=panel.y + NEW_GAME_SETUP.difficulty_label_y,
        font_size=difficulty_label_size,
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
    difficulty_text, difficulty_font_size = fit_text_to_rect(
        ui.new_game_difficulty or "Normal",
        rect_w=diff_rect.w - 20.0,
        rect_h=diff_rect.h - 4.0,
        base_font_size=20.0,
        min_font_size=12.0,
        pad_x=4.0,
        pad_y=1.0,
        overflow_policy="ellipsis",
    )
    renderer.add_text(
        key="newgame:difficulty",
        text=difficulty_text,
        x=diff_rect.x + 12.0,
        y=diff_rect.y + diff_rect.h / 2.0,
        font_size=difficulty_font_size,
        color=TOKENS.text_primary,
        anchor="middle-left",
    )
    if ui.new_game_difficulty_open:
        for idx, name in enumerate(ui.new_game_difficulty_options):
            option = NEW_GAME_SETUP.difficulty_option_rect(idx)
            color = (
                active_theme.primary_button_border
                if name == ui.new_game_difficulty
                else active_theme.panel_border
            )
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
                min_font_size=10.0,
                pad_x=4.0,
                pad_y=1.0,
                overflow_policy="ellipsis",
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
        color=active_theme.panel_border,
        z=0.89,
    )
    presets_title_text, presets_title_size = fit_text_to_rect(
        "Available Presets",
        rect_w=list_rect.w - 24.0,
        rect_h=24.0,
        base_font_size=16.0,
        min_font_size=10.0,
        pad_x=4.0,
        pad_y=1.0,
        overflow_policy="ellipsis",
    )
    renderer.add_text(
        key="newgame:presets:title",
        text=presets_title_text,
        x=list_rect.x + 12.0,
        y=list_rect.y + 10.0,
        font_size=presets_title_size,
        color=TOKENS.text_muted,
        anchor="top-left",
        z=0.9,
    )
    for idx, name in enumerate(ui.new_game_visible_presets):
        row = NEW_GAME_SETUP.preset_row_rect(idx)
        color = (
            active_theme.primary_button_border
            if name == ui.new_game_selected_preset
            else TOKENS.surface_elevated
        )
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
        row_text, row_font_size, _ = project_text_fit(
            TextFitSpec(
                text=name,
                rect=Rect(row.x + 8.0, row.y + 2.0, row.w - 16.0, row.h - 4.0),
                base_font_size=16.0,
                overflow_policy="ellipsis",
                parent=row,
                enforce_parent=True,
            )
        )
        renderer.add_text(
            key=f"newgame:preset:text:{name}",
            text=row_text,
            x=row.x + 12.0,
            y=row.y + row.h / 2.0,
            font_size=row_font_size,
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
        color=active_theme.primary_button_bg,
        z=0.9,
    )
    draw_rounded_rect(
        renderer,
        key="newgame:random:border",
        x=random_btn.x,
        y=random_btn.y,
        w=random_btn.w,
        h=random_btn.h,
        radius=7.0,
        color=active_theme.primary_button_border,
        z=0.91,
    )
    draw_rounded_rect(
        renderer,
        key="newgame:random:border:inner",
        x=random_btn.x + 1.0,
        y=random_btn.y + 1.0,
        w=max(1.0, random_btn.w - 2.0),
        h=max(1.0, random_btn.h - 2.0),
        radius=6.0,
        color=active_theme.primary_button_bg,
        z=0.911,
    )
    draw_rounded_rect(
        renderer,
        key="newgame:random:highlight",
        x=random_btn.x + 1.0,
        y=random_btn.y + 1.0,
        w=max(1.0, random_btn.w - 2.0),
        h=max(1.0, (random_btn.h * 0.45) - 1.0),
        radius=6.0,
        color=active_theme.primary_button_highlight,
        z=0.912,
    )
    random_text, random_font_size = fit_text_to_rect(
        "Generate Random Fleet",
        rect_w=random_btn.w,
        rect_h=random_btn.h,
        base_font_size=14.0,
        min_font_size=10.0,
        pad_x=4.0,
        pad_y=1.0,
        overflow_policy="ellipsis",
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

    preview_title_text, preview_title_size = fit_text_to_rect(
        f"Selected Setup: {ui.new_game_source or 'None'}",
        rect_w=panel.w - NEW_GAME_SETUP.preview_x - 20.0,
        rect_h=28.0,
        base_font_size=20.0,
        min_font_size=12.0,
        pad_x=4.0,
        pad_y=1.0,
        overflow_policy="ellipsis",
    )
    renderer.add_text(
        key="newgame:preview_title",
        text=preview_title_text,
        x=panel.x + NEW_GAME_SETUP.preview_x,
        y=panel.y + NEW_GAME_SETUP.preview_title_y,
        font_size=preview_title_size,
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

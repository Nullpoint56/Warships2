"""Rendering for new-game setup screen."""

from __future__ import annotations

from warships.game.app.ui_state import AppUIState
from warships.game.ui.layout_metrics import NEW_GAME_SETUP
from warships.game.ui.views.common import draw_preset_preview, truncate


def draw_new_game_setup(renderer, ui: AppUIState) -> None:
    panel = NEW_GAME_SETUP.panel_rect()
    renderer.add_rect("newgame:panel", panel.x, panel.y, panel.w, panel.h, "#0f172a", z=0.85)
    renderer.add_text(
        key="newgame:title",
        text="New Game Setup",
        x=panel.x + 20.0,
        y=panel.y + 20.0,
        font_size=30.0,
        color="#dbeafe",
        anchor="top-left",
    )
    renderer.add_text(
        key="newgame:difficulty_label",
        text="Difficulty",
        x=panel.x + 20.0,
        y=panel.y + NEW_GAME_SETUP.difficulty_label_y,
        font_size=16.0,
        color="#bfdbfe",
        anchor="top-left",
    )
    diff_rect = NEW_GAME_SETUP.difficulty_rect()
    renderer.add_rect("newgame:diff:bg", diff_rect.x, diff_rect.y, diff_rect.w, diff_rect.h, "#1e293b", z=0.9)
    renderer.add_text(
        key="newgame:difficulty",
        text=ui.new_game_difficulty or "Normal",
        x=diff_rect.x + 12.0,
        y=diff_rect.y + diff_rect.h / 2.0,
        font_size=20.0,
        color="#e2e8f0",
        anchor="middle-left",
    )
    if ui.new_game_difficulty_open:
        for idx, name in enumerate(ui.new_game_difficulty_options):
            option = NEW_GAME_SETUP.difficulty_option_rect(idx)
            color = "#2563eb" if name == ui.new_game_difficulty else "#334155"
            renderer.add_rect(f"newgame:diff:opt:bg:{name}", option.x, option.y, option.w, option.h, color, z=0.95)
            renderer.add_text(
                key=f"newgame:diff:opt:text:{name}",
                text=name,
                x=option.x + 10.0,
                y=option.y + option.h / 2.0,
                font_size=16.0,
                color="#e2e8f0",
                anchor="middle-left",
                z=0.96,
            )

    list_rect = NEW_GAME_SETUP.preset_list_rect()
    renderer.add_rect("newgame:presets:bg", list_rect.x, list_rect.y, list_rect.w, list_rect.h, "#111827", z=0.88)
    renderer.add_text(
        key="newgame:presets:title",
        text="Available Presets",
        x=list_rect.x + 12.0,
        y=list_rect.y + 10.0,
        font_size=16.0,
        color="#bfdbfe",
        anchor="top-left",
        z=0.9,
    )
    for idx, name in enumerate(ui.new_game_visible_presets):
        row = NEW_GAME_SETUP.preset_row_rect(idx)
        color = "#2563eb" if name == ui.new_game_selected_preset else "#1f2937"
        renderer.add_rect(f"newgame:preset:row:{name}", row.x, row.y, row.w, row.h, color, z=0.9)
        renderer.add_text(
            key=f"newgame:preset:text:{name}",
            text=truncate(name, 36),
            x=row.x + 12.0,
            y=row.y + row.h / 2.0,
            font_size=16.0,
            color="#e5e7eb",
            anchor="middle-left",
            z=0.92,
        )
    random_btn = NEW_GAME_SETUP.random_button_rect()
    renderer.add_rect("newgame:random:bg", random_btn.x, random_btn.y, random_btn.w, random_btn.h, "#7c3aed", z=0.9)
    renderer.add_text(
        key="newgame:random:text",
        text="Generate Random Fleet",
        x=random_btn.x + random_btn.w / 2.0,
        y=random_btn.y + random_btn.h / 2.0,
        font_size=14.0,
        anchor="middle-center",
        z=0.92,
    )

    renderer.add_text(
        key="newgame:preview_title",
        text=f"Selected Setup: {ui.new_game_source or 'None'}",
        x=panel.x + NEW_GAME_SETUP.preview_x,
        y=panel.y + NEW_GAME_SETUP.preview_title_y,
        font_size=20.0,
        color="#bfdbfe",
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



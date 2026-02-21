"""Scene-specific color tuning for Warships UI."""

from __future__ import annotations

from dataclasses import dataclass

from engine.api.ui_style import DEFAULT_UI_STYLE_TOKENS
from warships.game.app.state_machine import AppState

TOKENS = DEFAULT_UI_STYLE_TOKENS


@dataclass(frozen=True, slots=True)
class SceneTheme:
    window_bg: str
    panel_bg: str
    panel_border: str
    panel_glow_top: str
    panel_pattern: str
    status_bg: str
    status_border: str
    board_bg: str
    board_grid: str
    board_border: str
    primary_button_bg: str
    primary_button_border: str
    primary_button_highlight: str
    secondary_button_bg: str
    secondary_button_border: str
    danger_button_bg: str
    danger_button_border: str


MAIN_MENU_THEME = SceneTheme(
    window_bg="#050f1f",
    panel_bg=TOKENS.surface_base,
    panel_border=TOKENS.border_subtle,
    panel_glow_top="#78b2ff2a",
    panel_pattern="#8abfff24",
    status_bg="#12356f",
    status_border="#5f95ee",
    board_bg=TOKENS.board_bg,
    board_grid=TOKENS.board_grid,
    board_border=TOKENS.border_accent,
    primary_button_bg="#1a64e8",
    primary_button_border="#6ea3ff",
    primary_button_highlight="#ffffff33",
    secondary_button_bg="#1a2f4a",
    secondary_button_border="#5475a3",
    danger_button_bg="#cc3f4b",
    danger_button_border="#ef7680",
)

NEW_GAME_THEME = SceneTheme(
    window_bg="#0a1a30",
    panel_bg="#182b46",
    panel_border="#4b688f",
    panel_glow_top="#9fd0ff33",
    panel_pattern="#b5d8ff30",
    status_bg="#1a406f",
    status_border="#73a6ea",
    board_bg=TOKENS.board_bg,
    board_grid=TOKENS.board_grid,
    board_border=TOKENS.border_accent,
    primary_button_bg="#2d7eff",
    primary_button_border="#8ab6ff",
    primary_button_highlight="#ffffff3b",
    secondary_button_bg="#213852",
    secondary_button_border="#5f81ac",
    danger_button_bg="#cf3f4a",
    danger_button_border="#ee747d",
)

PRESET_THEME = SceneTheme(
    window_bg="#081a22",
    panel_bg="#123040",
    panel_border="#3f7593",
    panel_glow_top="#78dcff30",
    panel_pattern="#80dcff2d",
    status_bg="#17435f",
    status_border="#59abcf",
    board_bg=TOKENS.board_bg,
    board_grid=TOKENS.board_grid,
    board_border=TOKENS.border_accent,
    primary_button_bg="#1a8fc2",
    primary_button_border="#64c4e8",
    primary_button_highlight="#ffffff36",
    secondary_button_bg="#1b3b4c",
    secondary_button_border="#5b879e",
    danger_button_bg="#cb3f4a",
    danger_button_border="#eb7079",
)

PLACEMENT_THEME = SceneTheme(
    window_bg="#091320",
    panel_bg="#1a2d44",
    panel_border="#4a6788",
    panel_glow_top="#7fb8ff28",
    panel_pattern="#9fc4ff20",
    status_bg="#213d60",
    status_border="#6390c9",
    board_bg="#1d478f",
    board_grid="#89bbff",
    board_border="#6b9be0",
    primary_button_bg="#2b72e3",
    primary_button_border="#74a2eb",
    primary_button_highlight="#ffffff34",
    secondary_button_bg="#22394f",
    secondary_button_border="#6285ab",
    danger_button_bg="#cc414d",
    danger_button_border="#eb737d",
)


def theme_for_state(state: AppState) -> SceneTheme:
    if state is AppState.MAIN_MENU:
        return MAIN_MENU_THEME
    if state is AppState.NEW_GAME_SETUP:
        return NEW_GAME_THEME
    if state is AppState.PRESET_MANAGE:
        return PRESET_THEME
    if state in (AppState.PLACEMENT_EDIT, AppState.BATTLE, AppState.RESULT):
        return PLACEMENT_THEME
    return MAIN_MENU_THEME

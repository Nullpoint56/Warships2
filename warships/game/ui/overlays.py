"""HUD/status overlays and button controls."""

from __future__ import annotations

from engine.ui_runtime.widgets import Button
from warships.game.app.state_machine import AppState
from warships.game.ui.layout_metrics import top_bar_rect


def buttons_for_state(
    state: AppState,
    placement_ready: bool,
    has_presets: bool,
) -> list[Button]:
    """Build buttons for the current app state."""
    top_bar = top_bar_rect()
    base_y = top_bar.y + 8.0
    left_x = top_bar.x + 20.0
    gap = 16.0
    bw = 160.0
    bh = 50.0

    if state is AppState.MAIN_MENU:
        return [
            Button("new_game", left_x, base_y, bw, bh),
            Button("manage_presets", left_x + bw + gap, base_y, bw + 30.0, bh),
            Button("quit", left_x + 2 * (bw + gap) + 30.0, base_y, bw, bh),
        ]
    if state is AppState.NEW_GAME_SETUP:
        return [
            Button("start_game", left_x + 430.0, base_y, bw + 20.0, bh),
            Button("back_main", left_x + 630.0, base_y, bw, bh),
        ]
    if state is AppState.PRESET_MANAGE:
        return [
            Button("create_preset", left_x, base_y, bw, bh),
            Button("back_main", left_x + bw + gap, base_y, bw, bh),
        ]
    if state is AppState.PLACEMENT_EDIT:
        return [
            Button("randomize", left_x, base_y, bw, bh),
            Button("save_preset", left_x + 2 * (bw + gap), base_y, bw, bh, enabled=placement_ready),
            Button("back_to_presets", left_x + 3 * (bw + gap), base_y, bw + 30.0, bh),
        ]
    if state is AppState.BATTLE:
        return [Button("back_main", left_x, base_y, bw, bh)]
    if state is AppState.RESULT:
        return [
            Button("play_again", left_x, base_y, bw, bh),
            Button("back_main", left_x + bw + gap, base_y, bw + 20.0, bh),
        ]
    return []


def button_label(button_id: str) -> str:
    """Map button id to visible label."""
    if button_id.startswith("preset_edit:"):
        return "Edit"
    if button_id.startswith("preset_rename:"):
        return "Rename"
    if button_id.startswith("preset_delete:"):
        return "Delete"
    if button_id.startswith("new_game_diff_option:"):
        return button_id.split(":", 1)[1]
    if button_id.startswith("new_game_select_preset:"):
        return button_id.split(":", 1)[1]
    labels = {
        "manage_presets": "Manage Presets",
        "new_game": "New Game",
        "create_preset": "Create Preset",
        "back_main": "Main Menu",
        "quit": "Quit",
        "new_game_toggle_difficulty": "Difficulty",
        "new_game_randomize": "Random Fleet",
        "start_game": "Start Game",
        "save_preset": "Save Preset",
        "randomize": "Randomize",
        "back_to_presets": "Back to Presets",
        "menu_from_battle": "Menu",
        "play_again": "Play Again",
        "prompt_confirm_save": "Save",
        "prompt_confirm_rename": "Rename",
        "prompt_confirm_overwrite": "Overwrite",
        "prompt_cancel": "Cancel",
    }
    return labels.get(button_id, button_id)


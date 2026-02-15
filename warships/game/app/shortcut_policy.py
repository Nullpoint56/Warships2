"""Keyboard shortcut policy per app state."""

from __future__ import annotations

from warships.game.app.state_machine import AppState


def shortcut_buttons_for_state(state: AppState) -> dict[str, str]:
    """Return normalized key-to-button shortcuts for a given app state."""
    if state is AppState.MAIN_MENU:
        return {"enter": "new_game"}
    if state is AppState.NEW_GAME_SETUP:
        return {"enter": "start_game", "escape": "back_main"}
    if state is AppState.PRESET_MANAGE:
        return {"enter": "create_preset", "escape": "back_main"}
    if state is AppState.PLACEMENT_EDIT:
        return {"enter": "save_preset", "escape": "back_to_presets"}
    if state is AppState.BATTLE:
        return {"escape": "back_main"}
    if state is AppState.RESULT:
        return {"enter": "play_again"}
    return {}

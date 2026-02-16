from warships.game.app.shortcut_policy import shortcut_buttons_for_state
from warships.game.app.state_machine import AppState


def test_shortcut_policy_by_state() -> None:
    assert shortcut_buttons_for_state(AppState.MAIN_MENU) == {"enter": "new_game"}
    assert shortcut_buttons_for_state(AppState.NEW_GAME_SETUP) == {"enter": "start_game", "escape": "back_main"}
    assert shortcut_buttons_for_state(AppState.PRESET_MANAGE) == {"enter": "create_preset", "escape": "back_main"}
    assert shortcut_buttons_for_state(AppState.PLACEMENT_EDIT) == {"enter": "save_preset", "escape": "back_to_presets"}
    assert shortcut_buttons_for_state(AppState.BATTLE) == {"escape": "back_main"}
    assert shortcut_buttons_for_state(AppState.RESULT) == {"enter": "play_again"}

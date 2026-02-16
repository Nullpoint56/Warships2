from warships.game.app.state_machine import AppState
from warships.game.ui.overlays import button_label, buttons_for_state


def test_buttons_for_state_presence() -> None:
    assert any(b.id == "new_game" for b in buttons_for_state(AppState.MAIN_MENU, False, False))
    assert any(
        b.id == "start_game" for b in buttons_for_state(AppState.NEW_GAME_SETUP, False, False)
    )
    assert any(
        b.id == "create_preset" for b in buttons_for_state(AppState.PRESET_MANAGE, False, True)
    )
    placement = buttons_for_state(AppState.PLACEMENT_EDIT, placement_ready=True, has_presets=True)
    assert any(b.id == "save_preset" and b.enabled for b in placement)


def test_button_label_mapping() -> None:
    assert button_label("manage_presets") == "Manage Presets"
    assert button_label("new_game_diff_option:Hard") == "Hard"
    assert button_label("new_game_select_preset:alpha") == "alpha"
    assert button_label("unknown") == "unknown"

from warships.game.app.services.input_policy import (
    can_handle_key_for_placement,
    can_handle_pointer_down,
    can_handle_pointer_move,
    can_handle_pointer_release,
    pointer_down_action,
    resolve_wheel_target,
)
from warships.game.app.state_machine import AppState
from warships.game.ui.layout_metrics import NEW_GAME_SETUP, PRESET_PANEL


def test_input_policy_basic_state_gates() -> None:
    assert can_handle_pointer_move(AppState.PLACEMENT_EDIT)
    assert not can_handle_pointer_move(AppState.MAIN_MENU)
    assert can_handle_pointer_release(AppState.PLACEMENT_EDIT, 1)
    assert not can_handle_pointer_release(AppState.PLACEMENT_EDIT, 2)
    assert can_handle_key_for_placement(AppState.PLACEMENT_EDIT)
    assert not can_handle_key_for_placement(AppState.BATTLE)
    assert can_handle_pointer_down(AppState.PLACEMENT_EDIT, has_prompt=False)
    assert not can_handle_pointer_down(AppState.PLACEMENT_EDIT, has_prompt=True)


def test_pointer_down_action_mapping() -> None:
    assert pointer_down_action(1) == "left"
    assert pointer_down_action(2) == "right"
    assert pointer_down_action(3) is None


def test_resolve_wheel_target_regions() -> None:
    ng = NEW_GAME_SETUP.preset_list_rect()
    pm = PRESET_PANEL.panel_rect()
    assert resolve_wheel_target(AppState.NEW_GAME_SETUP, ng.x + 1, ng.y + 1) == "new_game_presets"
    assert resolve_wheel_target(AppState.PRESET_MANAGE, pm.x + 1, pm.y + 1) == "preset_manage"
    assert resolve_wheel_target(AppState.MAIN_MENU, 0, 0) is None

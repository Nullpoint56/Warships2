"""Tests for pygfx UI interaction routing framework."""

from warships.app.state_machine import AppState
from warships.app.ui_state import AppUIState
from warships.core.models import Orientation, ShipType
from warships.ui.framework import can_scroll_with_wheel, build_interaction_plan, resolve_key_shortcut, resolve_pointer_button
from warships.ui.layout_metrics import NEW_GAME_SETUP, PRESET_PANEL
from warships.ui.overlays import Button


def _ui_state(state: AppState, buttons: list[Button]) -> AppUIState:
    return AppUIState(
        state=state,
        status="status",
        buttons=buttons,
        placements=[],
        placement_orientation=Orientation.HORIZONTAL,
        session=None,
        ship_order=[ShipType.CARRIER],
        is_closing=False,
        preset_rows=[],
        prompt=None,
        held_ship_type=None,
        held_ship_orientation=None,
        held_grab_index=0,
        hover_cell=None,
        hover_x=None,
        hover_y=None,
        new_game_difficulty=None,
        new_game_difficulty_open=False,
        new_game_difficulty_options=[],
        new_game_visible_presets=[],
        new_game_selected_preset=None,
        new_game_can_scroll_up=False,
        new_game_can_scroll_down=False,
        new_game_source=None,
        new_game_preview=[],
    )


def test_pointer_resolution_ignores_disabled_buttons() -> None:
    ui = _ui_state(
        AppState.PLACEMENT_EDIT,
        buttons=[
            Button("save_preset", 10.0, 10.0, 100.0, 40.0, enabled=False),
            Button("back_to_presets", 10.0, 10.0, 100.0, 40.0, enabled=True),
        ],
    )
    plan = build_interaction_plan(ui)
    assert resolve_pointer_button(plan, 20.0, 20.0) == "back_to_presets"


def test_shortcuts_main_menu_and_battle() -> None:
    main_plan = build_interaction_plan(_ui_state(AppState.MAIN_MENU, buttons=[]))
    battle_plan = build_interaction_plan(_ui_state(AppState.BATTLE, buttons=[]))
    assert resolve_key_shortcut(main_plan, "enter") == "new_game"
    assert resolve_key_shortcut(main_plan, "escape") is None
    assert resolve_key_shortcut(battle_plan, "escape") == "back_main"


def test_wheel_scroll_only_inside_new_game_preset_list() -> None:
    new_game_plan = build_interaction_plan(_ui_state(AppState.NEW_GAME_SETUP, buttons=[]))
    preset_manage_plan = build_interaction_plan(_ui_state(AppState.PRESET_MANAGE, buttons=[]))
    battle_plan = build_interaction_plan(_ui_state(AppState.BATTLE, buttons=[]))
    list_rect = NEW_GAME_SETUP.preset_list_rect()
    preset_panel = PRESET_PANEL.panel_rect()
    assert can_scroll_with_wheel(new_game_plan, list_rect.x + 5.0, list_rect.y + 5.0) is True
    assert can_scroll_with_wheel(new_game_plan, 1.0, 1.0) is False
    assert can_scroll_with_wheel(preset_manage_plan, preset_panel.x + 5.0, preset_panel.y + 5.0) is True
    assert can_scroll_with_wheel(battle_plan, list_rect.x + 5.0, list_rect.y + 5.0) is False

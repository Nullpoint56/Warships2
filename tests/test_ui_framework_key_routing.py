"""Tests for framework key routing helpers."""

from warships.app.state_machine import AppState
from warships.app.ui_state import AppUIState
from warships.core.models import Orientation, ShipType
from warships.ui.framework import build_interaction_plan, map_key_name, route_non_modal_key_event


def _ui_state(state: AppState) -> AppUIState:
    return AppUIState(
        state=state,
        status="status",
        buttons=[],
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


def test_map_key_name_normalizes_special_and_alpha_keys() -> None:
    assert map_key_name("Enter") == "enter"
    assert map_key_name("Escape") == "escape"
    assert map_key_name("R") == "r"
    assert map_key_name("x") == "x"
    assert map_key_name("Shift") is None


def test_route_non_modal_key_event_char_and_shortcut() -> None:
    main_plan = build_interaction_plan(_ui_state(AppState.MAIN_MENU))
    char_route = route_non_modal_key_event("char", "a", main_plan)
    assert char_route.controller_char == "a"
    assert char_route.controller_key is None

    enter_route = route_non_modal_key_event("key_down", "Enter", main_plan)
    assert enter_route.controller_key == "enter"
    assert enter_route.shortcut_button_id == "new_game"


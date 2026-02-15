"""Tests for modal input runtime routing."""

from warships.app.state_machine import AppState
from warships.app.ui_state import AppUIState, TextPromptView
from warships.core.models import Orientation, ShipType
from warships.ui.framework import (
    ModalInputState,
    build_modal_text_input_widget,
    route_modal_key_event,
    route_modal_pointer_event,
)


def _ui_state(prompt: TextPromptView | None) -> AppUIState:
    return AppUIState(
        state=AppState.PRESET_MANAGE,
        status="status",
        buttons=[],
        placements=[],
        placement_orientation=Orientation.HORIZONTAL,
        session=None,
        ship_order=[ShipType.CARRIER],
        is_closing=False,
        preset_rows=[],
        prompt=prompt,
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


def _widget() -> object:
    prompt = TextPromptView(
        title="Save Preset",
        value="fleet",
        confirm_button_id="prompt_confirm_save",
        cancel_button_id="prompt_cancel",
    )
    widget = build_modal_text_input_widget(_ui_state(prompt))
    assert widget is not None
    return widget


def test_modal_state_sync_focuses_input_on_open() -> None:
    state = ModalInputState()
    widget = _widget()
    state.sync(widget)
    assert state.is_open is True
    assert state.input_focused is True
    state.input_focused = False
    state.sync(widget)
    assert state.input_focused is False
    state.sync(None)
    assert state.is_open is False
    assert state.input_focused is False


def test_modal_pointer_routing_sets_focus_and_buttons() -> None:
    state = ModalInputState(is_open=True, input_focused=True)
    widget = _widget()
    input_rect = widget.input_rect
    confirm = widget.confirm_button_rect
    overlay_x = widget.overlay_rect.x + 1.0
    overlay_y = widget.overlay_rect.y + 1.0

    route = route_modal_pointer_event(widget, state, confirm.x + 1.0, confirm.y + 1.0, 1)
    assert route.button_id == "prompt_confirm_save"

    route = route_modal_pointer_event(widget, state, input_rect.x + 1.0, input_rect.y + 1.0, 1)
    assert route.focus_input is True

    route = route_modal_pointer_event(widget, state, overlay_x, overlay_y, 1)
    assert route.focus_input is False


def test_modal_key_routing_respects_focus() -> None:
    state = ModalInputState(is_open=True, input_focused=False)
    route = route_modal_key_event("char", "a", None, state)
    assert route.char is None
    state.input_focused = True
    route = route_modal_key_event("char", "a", None, state)
    assert route.char == "a"
    route = route_modal_key_event("key_down", "Enter", "enter", state)
    assert route.key == "enter"


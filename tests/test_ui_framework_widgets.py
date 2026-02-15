"""Tests for reusable modal text-input widgets."""

from warships.app.state_machine import AppState
from warships.app.ui_state import AppUIState, TextPromptView
from warships.core.models import Orientation, ShipType
from warships.ui.framework import build_modal_text_input_widget, resolve_modal_pointer_target
from warships.ui.layout_metrics import PROMPT


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


def test_build_modal_text_input_widget_returns_none_without_prompt() -> None:
    assert build_modal_text_input_widget(_ui_state(prompt=None)) is None


def test_build_modal_text_input_widget_uses_prompt_and_layout() -> None:
    prompt = TextPromptView(
        title="Save Preset",
        value="fleet_alpha",
        confirm_button_id="prompt_confirm_save",
        cancel_button_id="prompt_cancel",
    )
    widget = build_modal_text_input_widget(_ui_state(prompt=prompt))
    assert widget is not None
    assert widget.title == "Save Preset"
    assert widget.value == "fleet_alpha"
    assert widget.confirm_button_id == "prompt_confirm_save"
    assert widget.cancel_button_id == "prompt_cancel"
    assert widget.panel_rect == PROMPT.panel_rect()
    assert widget.input_rect == PROMPT.input_rect()
    assert widget.confirm_button_rect == PROMPT.confirm_button_rect()
    assert widget.cancel_button_rect == PROMPT.cancel_button_rect()


def test_modal_pointer_target_resolution() -> None:
    prompt = TextPromptView(
        title="Rename",
        value="fleet_beta",
        confirm_button_id="prompt_confirm_rename",
        cancel_button_id="prompt_cancel",
    )
    widget = build_modal_text_input_widget(_ui_state(prompt=prompt))
    assert widget is not None
    confirm = widget.confirm_button_rect
    cancel = widget.cancel_button_rect
    input_rect = widget.input_rect
    panel = widget.panel_rect
    assert resolve_modal_pointer_target(widget, confirm.x + 1.0, confirm.y + 1.0) == "confirm"
    assert resolve_modal_pointer_target(widget, cancel.x + 1.0, cancel.y + 1.0) == "cancel"
    assert resolve_modal_pointer_target(widget, input_rect.x + 1.0, input_rect.y + 1.0) == "input"
    assert resolve_modal_pointer_target(widget, panel.x + 1.0, panel.y + 1.0) in {"panel", "input"}
    assert resolve_modal_pointer_target(widget, 1.0, 1.0) == "overlay"

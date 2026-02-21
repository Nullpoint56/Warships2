from engine.ui_runtime.widgets import Button
from tests.warships.unit.ui.helpers import FakeRenderer
from warships.game.app.state_machine import AppState
from warships.game.app.ui_state import AppUIState
from warships.game.core.models import Orientation
from warships.game.ui.framework.widgets import (
    build_modal_text_input_widget,
    render_modal_text_input_widget,
    resolve_modal_pointer_target,
)


class _Prompt:
    def __init__(self) -> None:
        self.title = "Save"
        self.value = "alpha"
        self.confirm_button_id = "prompt_confirm_save"
        self.cancel_button_id = "prompt_cancel"


def _ui_with_prompt(prompt) -> AppUIState:
    return AppUIState(
        state=AppState.MAIN_MENU,
        status="x",
        buttons=[Button("new_game", 0, 0, 10, 10)],
        placements=[],
        placement_orientation=Orientation.HORIZONTAL,
        session=None,
        ship_order=[],
        is_closing=False,
        preset_rows=[],
        prompt=prompt,
        held_ship_type=None,
        held_ship_orientation=None,
        held_grab_index=0,
        hover_cell=None,
        hover_x=None,
        hover_y=None,
        held_preview_valid=True,
        held_preview_reason=None,
        placement_popup_message=None,
        new_game_difficulty="Normal",
        new_game_difficulty_open=False,
        new_game_difficulty_options=["Easy", "Normal", "Hard"],
        new_game_visible_presets=[],
        new_game_selected_preset=None,
        new_game_can_scroll_up=False,
        new_game_can_scroll_down=False,
        new_game_source=None,
        new_game_preview=[],
        preset_manage_can_scroll_up=False,
        preset_manage_can_scroll_down=False,
    )


def test_build_modal_widget_and_pointer_targets() -> None:
    ui = _ui_with_prompt(_Prompt())
    widget = build_modal_text_input_widget(ui)
    assert widget is not None
    assert (
        resolve_modal_pointer_target(
            widget, widget.confirm_button_rect.x + 1, widget.confirm_button_rect.y + 1
        )
        == "confirm"
    )
    assert (
        resolve_modal_pointer_target(
            widget, widget.cancel_button_rect.x + 1, widget.cancel_button_rect.y + 1
        )
        == "cancel"
    )
    assert (
        resolve_modal_pointer_target(widget, widget.input_rect.x + 1, widget.input_rect.y + 1)
        == "input"
    )


def test_build_modal_widget_none_when_prompt_missing() -> None:
    ui = _ui_with_prompt(None)
    assert build_modal_text_input_widget(ui) is None


def test_modal_prompt_title_does_not_collapse_to_single_character() -> None:
    prompt = _Prompt()
    prompt.title = "Save Preset"
    ui = _ui_with_prompt(prompt)
    widget = build_modal_text_input_widget(ui)
    assert widget is not None
    renderer = FakeRenderer()

    render_modal_text_input_widget(renderer, widget)

    title_calls = [kwargs for _args, kwargs in renderer.texts if kwargs.get("key") == "prompt:title"]
    assert title_calls
    text = str(title_calls[0].get("text", ""))
    assert len(text) >= 4

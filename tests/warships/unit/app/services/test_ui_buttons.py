from warships.game.app.services.new_game_flow import DIFFICULTIES
from warships.game.app.services.prompt_flow import PromptFlowService
from warships.game.app.services.ui_buttons import (
    compose_buttons,
    new_game_setup_buttons,
    preset_row_buttons,
    prompt_buttons,
)
from warships.game.app.state_machine import AppState
from warships.game.app.ui_state import PresetRowView
from warships.game.core.models import Coord, Orientation, ShipPlacement, ShipType


def _row(name: str) -> PresetRowView:
    return PresetRowView(
        name=name,
        placements=[ShipPlacement(ShipType.DESTROYER, Coord(0, 0), Orientation.HORIZONTAL)],
    )


def test_prompt_and_preset_row_buttons_build_expected_ids() -> None:
    prompt_state = PromptFlowService.open_prompt("Save", "x", mode="save")
    buttons = prompt_buttons(prompt_state.prompt)
    assert [b.id for b in buttons] == ["prompt_confirm_save", "prompt_cancel"]

    rows = [_row("alpha"), _row("beta")]
    row_buttons = preset_row_buttons(rows)
    ids = [b.id for b in row_buttons]
    assert "preset_edit:alpha" in ids
    assert "preset_rename:alpha" in ids
    assert "preset_delete:alpha" in ids
    assert "preset_edit:beta" in ids
    assert len(row_buttons) == 6


def test_new_game_setup_buttons_include_difficulty_and_random() -> None:
    rows = [_row("a"), _row("b"), _row("c")]
    buttons = new_game_setup_buttons(
        rows=rows,
        scroll=0,
        visible_rows=2,
        difficulty_open=True,
    )
    ids = [b.id for b in buttons]
    assert "new_game_toggle_difficulty" in ids
    assert "new_game_randomize" in ids
    assert "new_game_select_preset:a" in ids
    assert "new_game_select_preset:b" in ids
    for difficulty in DIFFICULTIES:
        assert f"new_game_diff_option:{difficulty}" in ids


def test_compose_buttons_state_specific_additions() -> None:
    preset_rows = [_row("one"), _row("two"), _row("three")]
    visible_manage_rows = [_row("two")]
    prompt = PromptFlowService.open_prompt("Rename", "x", mode="rename").prompt

    main_buttons = compose_buttons(
        state=AppState.MAIN_MENU,
        placement_ready=False,
        has_presets=True,
        visible_preset_manage_rows=[],
        preset_rows=preset_rows,
        new_game_preset_scroll=0,
        new_game_visible_rows=2,
        new_game_difficulty_open=False,
        prompt=None,
    )
    assert any(b.id == "new_game" for b in main_buttons)
    assert all(not b.id.startswith("preset_edit:") for b in main_buttons)

    preset_manage_buttons = compose_buttons(
        state=AppState.PRESET_MANAGE,
        placement_ready=False,
        has_presets=True,
        visible_preset_manage_rows=visible_manage_rows,
        preset_rows=preset_rows,
        new_game_preset_scroll=0,
        new_game_visible_rows=2,
        new_game_difficulty_open=False,
        prompt=None,
    )
    assert any(b.id == "create_preset" for b in preset_manage_buttons)
    assert any(b.id.startswith("preset_edit:") for b in preset_manage_buttons)

    new_game_buttons = compose_buttons(
        state=AppState.NEW_GAME_SETUP,
        placement_ready=False,
        has_presets=True,
        visible_preset_manage_rows=[],
        preset_rows=preset_rows,
        new_game_preset_scroll=1,
        new_game_visible_rows=2,
        new_game_difficulty_open=True,
        prompt=prompt,
    )
    new_game_ids = [b.id for b in new_game_buttons]
    assert "start_game" in new_game_ids
    assert "new_game_toggle_difficulty" in new_game_ids
    assert any(item.startswith("new_game_select_preset:") for item in new_game_ids)
    assert "prompt_confirm_rename" in new_game_ids

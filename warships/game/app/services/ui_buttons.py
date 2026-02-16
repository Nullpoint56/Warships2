"""UI button projection helpers extracted from controller."""

from __future__ import annotations

from warships.game.app.state_machine import AppState
from warships.game.app.ports.runtime_primitives import Button, PromptView
from warships.game.app.services.new_game_flow import DIFFICULTIES
from warships.game.app.services.preset_flow import PresetFlowService
from warships.game.app.ui_state import PresetRowView
from warships.game.ui.layout_metrics import NEW_GAME_SETUP, PRESET_PANEL, PROMPT
from warships.game.ui.overlays import buttons_for_state


def prompt_buttons(prompt: PromptView) -> list[Button]:
    confirm = PROMPT.confirm_button_rect()
    cancel = PROMPT.cancel_button_rect()
    return [
        Button(prompt.confirm_button_id, confirm.x, confirm.y, confirm.w, confirm.h),
        Button(prompt.cancel_button_id, cancel.x, cancel.y, cancel.w, cancel.h),
    ]


def preset_row_buttons(rows: list[PresetRowView]) -> list[Button]:
    buttons: list[Button] = []
    for idx, row in enumerate(rows):
        edit_rect, rename_rect, delete_rect = PRESET_PANEL.action_button_rects(idx)
        buttons.append(Button(f"preset_edit:{row.name}", edit_rect.x, edit_rect.y, edit_rect.w, edit_rect.h))
        buttons.append(Button(f"preset_rename:{row.name}", rename_rect.x, rename_rect.y, rename_rect.w, rename_rect.h))
        buttons.append(Button(f"preset_delete:{row.name}", delete_rect.x, delete_rect.y, delete_rect.w, delete_rect.h))
    return buttons


def new_game_setup_buttons(
    *,
    rows: list[PresetRowView],
    scroll: int,
    visible_rows: int,
    difficulty_open: bool,
) -> list[Button]:
    buttons: list[Button] = []
    difficulty = NEW_GAME_SETUP.difficulty_rect()
    buttons.append(Button("new_game_toggle_difficulty", difficulty.x, difficulty.y, difficulty.w, difficulty.h))
    if difficulty_open:
        for idx, name in enumerate(DIFFICULTIES):
            rect = NEW_GAME_SETUP.difficulty_option_rect(idx)
            buttons.append(Button(f"new_game_diff_option:{name}", rect.x, rect.y, rect.w, rect.h))

    for idx, name in enumerate(PresetFlowService.visible_new_game_preset_names(rows, scroll, visible_rows)):
        row_rect = NEW_GAME_SETUP.preset_row_rect(idx)
        buttons.append(Button(f"new_game_select_preset:{name}", row_rect.x, row_rect.y, row_rect.w, row_rect.h))
    random_rect = NEW_GAME_SETUP.random_button_rect()
    buttons.append(Button("new_game_randomize", random_rect.x, random_rect.y, random_rect.w, random_rect.h))
    return buttons


def compose_buttons(
    *,
    state: AppState,
    placement_ready: bool,
    has_presets: bool,
    visible_preset_manage_rows: list[PresetRowView],
    preset_rows: list[PresetRowView],
    new_game_preset_scroll: int,
    new_game_visible_rows: int,
    new_game_difficulty_open: bool,
    prompt: PromptView | None,
) -> list[Button]:
    """Compose state, row, and modal buttons for current controller snapshot."""
    buttons = buttons_for_state(
        state=state,
        placement_ready=placement_ready,
        has_presets=has_presets,
    )
    if state is AppState.PRESET_MANAGE:
        buttons.extend(preset_row_buttons(visible_preset_manage_rows))
    if state is AppState.NEW_GAME_SETUP:
        buttons.extend(
            new_game_setup_buttons(
                rows=preset_rows,
                scroll=new_game_preset_scroll,
                visible_rows=new_game_visible_rows,
                difficulty_open=new_game_difficulty_open,
            )
        )
    if prompt is not None:
        buttons.extend(prompt_buttons(prompt))
    return buttons



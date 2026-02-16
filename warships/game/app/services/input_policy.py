"""Input routing policy helpers for controller event handlers."""

from __future__ import annotations

from typing import Literal

from warships.game.app.state_machine import AppState
from warships.game.ui.layout_metrics import NEW_GAME_SETUP, PRESET_PANEL

WheelTarget = Literal["new_game_presets", "preset_manage"]
PointerDownAction = Literal["left", "right"]


def can_handle_pointer_move(state: AppState) -> bool:
    """Return whether pointer move should be handled for placement interactions."""
    return state is AppState.PLACEMENT_EDIT


def can_handle_pointer_release(state: AppState, button: int) -> bool:
    """Return whether pointer release should be handled for placement drop."""
    return state is AppState.PLACEMENT_EDIT and button == 1


def can_handle_key_for_placement(state: AppState) -> bool:
    """Return whether placement key handlers are active."""
    return state is AppState.PLACEMENT_EDIT


def can_handle_pointer_down(state: AppState, has_prompt: bool) -> bool:
    """Return whether pointer down should enter placement editor handlers."""
    return state is AppState.PLACEMENT_EDIT and not has_prompt


def pointer_down_action(button: int) -> PointerDownAction | None:
    """Map raw pointer button to placement action channel."""
    if button == 1:
        return "left"
    if button == 2:
        return "right"
    return None


def resolve_wheel_target(state: AppState, x: float, y: float) -> WheelTarget | None:
    """Resolve wheel target region for current app state and pointer position."""
    if state is AppState.NEW_GAME_SETUP and NEW_GAME_SETUP.preset_list_rect().contains(x, y):
        return "new_game_presets"
    if state is AppState.PRESET_MANAGE and PRESET_PANEL.panel_rect().contains(x, y):
        return "preset_manage"
    return None

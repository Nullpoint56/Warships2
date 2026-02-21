"""Controller mutation orchestration helpers."""

from __future__ import annotations

from collections.abc import Callable

from warships.game.app.controller_state import ControllerState
from warships.game.app.services.battle import PlayerTurnResult
from warships.game.app.services.placement_flow import HeldShipState, PlacementActionResult
from warships.game.app.services.preset_flow import EditPresetResult
from warships.game.app.state_machine import AppState
from warships.game.core.models import ShipPlacement


def apply_placement_outcome(
    outcome: PlacementActionResult,
    *,
    state: ControllerState,
    refresh_buttons: Callable[[], None],
) -> bool:
    """Apply placement interaction mutation outcome."""
    if not outcome.handled:
        return False
    _apply_held_state(state, outcome.held_state)
    state.placement_popup_message = outcome.popup_message
    state.held_preview_reason = outcome.invalid_reason
    if outcome.status is not None:
        state.status = outcome.status
    if outcome.refresh_buttons:
        refresh_buttons()
    return True


def apply_battle_turn_outcome(
    turn: PlayerTurnResult,
    *,
    state: ControllerState,
    refresh_buttons: Callable[[], None],
) -> None:
    """Apply battle turn result to controller state."""
    state.status = turn.status
    if turn.winner is not None:
        state.app_state = AppState.RESULT
        refresh_buttons()


def apply_edit_preset_result(
    result: EditPresetResult,
    *,
    preset_name: str,
    state: ControllerState,
    reset_editor: Callable[[], None],
    apply_placements: Callable[[list[ShipPlacement]], None],
    refresh_buttons: Callable[[], None],
    announce_state: Callable[[], None],
) -> bool:
    """Apply preset edit-load outcome to controller state."""
    if not result.success:
        state.status = result.status
        return True
    state.app_state = AppState.PLACEMENT_EDIT
    reset_editor()
    apply_placements(result.placements)
    state.editing_preset_name = preset_name
    state.status = result.status
    refresh_buttons()
    announce_state()
    return True


def _apply_held_state(state: ControllerState, held: HeldShipState) -> None:
    state.held_ship_type = held.ship_type
    state.held_orientation = held.orientation
    state.held_previous = held.previous
    state.held_grab_index = held.grab_index
    if held.ship_type is None:
        state.held_preview_valid = True
        state.held_preview_reason = None

"""Transition execution helper for controller lifecycle hooks."""

from __future__ import annotations

from collections.abc import Callable

from warships.game.app.controller_state import ControllerState
from warships.game.app.services.session_flow import AppTransition


def apply_transition(
    transition: AppTransition,
    *,
    state: ControllerState,
    reset_editor: Callable[[], None],
    enter_new_game_setup: Callable[[], None],
    refresh_preset_rows: Callable[[], None],
    refresh_buttons: Callable[[], None],
    announce_state: Callable[[], None],
) -> None:
    """Apply transition core state and execute requested side-effect hooks."""
    state.app_state = transition.state
    state.status = transition.status
    if transition.clear_session:
        state.session = None
    if transition.reset_editor:
        reset_editor()
    if transition.clear_editing_preset_name:
        state.editing_preset_name = None
    if transition.enter_new_game_setup:
        enter_new_game_setup()
    if transition.refresh_preset_rows:
        refresh_preset_rows()
    if transition.refresh_buttons:
        refresh_buttons()
    if transition.announce_state:
        announce_state()

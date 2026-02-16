"""Prompt outcome orchestration helpers for controller handlers."""

from __future__ import annotations

from collections.abc import Callable

from warships.game.app.controller_state import ControllerState
from warships.game.app.ports.runtime_primitives import PromptInteractionOutcome, PromptState
from warships.game.app.services.prompt_flow import PromptConfirmOutcome
from warships.game.app.state_machine import AppState


def apply_prompt_interaction_outcome(
    outcome: PromptInteractionOutcome,
    *,
    state: ControllerState,
    confirm_prompt: Callable[[], bool],
    refresh_buttons: Callable[[], None],
) -> bool:
    """Apply prompt interaction outcome and run requested side effects."""
    if not outcome.handled:
        return False
    state.prompt_state = outcome.state
    if outcome.request_confirm:
        return confirm_prompt()
    if outcome.refresh_buttons:
        refresh_buttons()
    return True


def apply_prompt_confirm_outcome(
    outcome: PromptConfirmOutcome,
    *,
    state: ControllerState,
    refresh_preset_rows: Callable[[], None],
    refresh_buttons: Callable[[], None],
    announce_state: Callable[[], None],
) -> bool:
    """Apply prompt confirm outcome and run requested side effects."""
    if not outcome.handled:
        return False
    if outcome.status is not None:
        state.status = outcome.status
    state.pending_save_name = outcome.pending_save_name
    state.editing_preset_name = outcome.editing_preset_name
    state.prompt_state = PromptState(
        prompt=outcome.prompt,
        buffer=outcome.prompt_buffer,
        mode=outcome.prompt_mode,
        target=outcome.prompt_target,
    )
    if outcome.switch_to_preset_manage:
        state.app_state = AppState.PRESET_MANAGE
    if outcome.refresh_preset_rows:
        refresh_preset_rows()
    if outcome.refresh_buttons:
        refresh_buttons()
    if outcome.announce_state:
        announce_state()
    return True

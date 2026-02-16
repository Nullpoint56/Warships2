"""Generic prompt input runtime helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PromptView:
    """Prompt view-model with title/value and action button ids."""

    title: str
    value: str
    confirm_button_id: str
    cancel_button_id: str


@dataclass(frozen=True, slots=True)
class PromptState:
    """Current prompt input runtime state."""

    prompt: PromptView | None = None
    buffer: str = ""
    mode: str | None = None
    target: str | None = None


@dataclass(frozen=True, slots=True)
class PromptInteractionOutcome:
    """Outcome of prompt input routing before app-specific confirmation logic."""

    handled: bool
    state: PromptState
    request_confirm: bool = False
    refresh_buttons: bool = False


def open_prompt(
    *,
    title: str,
    initial_value: str,
    confirm_button_id: str,
    cancel_button_id: str = "prompt_cancel",
    mode: str | None = None,
    target: str | None = None,
) -> PromptState:
    """Create prompt state with initial buffer and prompt metadata."""
    return PromptState(
        prompt=PromptView(
            title=title,
            value=initial_value,
            confirm_button_id=confirm_button_id,
            cancel_button_id=cancel_button_id,
        ),
        buffer=initial_value,
        mode=mode,
        target=target,
    )


def close_prompt() -> PromptState:
    """Close prompt and reset prompt input state."""
    return PromptState()


def sync_prompt(state: PromptState, value: str) -> PromptState:
    """Sync prompt buffer and prompt value text."""
    prompt = state.prompt
    if prompt is None:
        return state
    return PromptState(
        prompt=PromptView(
            title=prompt.title,
            value=value,
            confirm_button_id=prompt.confirm_button_id,
            cancel_button_id=prompt.cancel_button_id,
        ),
        buffer=value,
        mode=state.mode,
        target=state.target,
    )


def handle_button(
    state: PromptState,
    button_id: str,
    *,
    confirm_button_ids: set[str],
) -> PromptInteractionOutcome:
    """Handle prompt button actions for cancel/confirm semantics."""
    if state.prompt is None:
        return PromptInteractionOutcome(handled=False, state=state)
    if button_id == state.prompt.cancel_button_id:
        return PromptInteractionOutcome(
            handled=True,
            state=close_prompt(),
            refresh_buttons=True,
        )
    if button_id in confirm_button_ids:
        return PromptInteractionOutcome(handled=True, state=state, request_confirm=True)
    return PromptInteractionOutcome(handled=False, state=state)


def handle_key(state: PromptState, key: str) -> PromptInteractionOutcome:
    """Handle prompt key interactions (backspace/enter/escape)."""
    if state.prompt is None:
        return PromptInteractionOutcome(handled=False, state=state)
    if key == "backspace":
        return PromptInteractionOutcome(
            handled=True,
            state=sync_prompt(state, state.buffer[:-1]),
        )
    if key == "enter":
        return PromptInteractionOutcome(handled=True, state=state, request_confirm=True)
    if key == "escape":
        return PromptInteractionOutcome(
            handled=True,
            state=close_prompt(),
            refresh_buttons=True,
        )
    return PromptInteractionOutcome(handled=False, state=state)


def handle_char(state: PromptState, ch: str, max_len: int = 32) -> PromptInteractionOutcome:
    """Handle prompt text input updates."""
    if state.prompt is None:
        return PromptInteractionOutcome(handled=False, state=state)
    if len(ch) != 1 or not ch.isprintable():
        return PromptInteractionOutcome(handled=False, state=state)
    if len(state.buffer) >= max_len:
        return PromptInteractionOutcome(handled=False, state=state)
    return PromptInteractionOutcome(
        handled=True,
        state=sync_prompt(state, state.buffer + ch),
    )

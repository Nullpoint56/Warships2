"""Generic dialog workflow helpers."""

from __future__ import annotations

from dataclasses import dataclass

from engine.api.ui_primitives import PromptState, open_prompt


@dataclass(frozen=True, slots=True)
class DialogOpenSpec:
    """Generic dialog-open parameters."""

    title: str
    initial_value: str
    mode: str
    confirm_button_id: str
    cancel_button_id: str = "prompt_cancel"
    target: str | None = None


def resolve_confirm_button_id(mode: str, mapping: dict[str, str], default_id: str) -> str:
    """Resolve confirm action button id from mode using caller-provided mapping."""
    return mapping.get(mode, default_id)


def open_dialog(spec: DialogOpenSpec) -> PromptState:
    """Open a dialog as generic prompt state."""
    return open_prompt(
        title=spec.title,
        initial_value=spec.initial_value,
        confirm_button_id=spec.confirm_button_id,
        cancel_button_id=spec.cancel_button_id,
        mode=spec.mode,
        target=spec.target,
    )


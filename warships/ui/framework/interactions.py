"""Declarative interaction routing for UI state."""

from __future__ import annotations

from dataclasses import dataclass

from warships.app.state_machine import AppState
from warships.app.ui_state import AppUIState
from warships.ui.layout_metrics import NEW_GAME_SETUP
from warships.ui.overlays import Button


@dataclass(frozen=True, slots=True)
class InteractionPlan:
    """Precomputed click/shortcut routing for a UI state snapshot."""

    buttons: tuple[Button, ...]
    shortcut_buttons: dict[str, str]
    allows_ai_board_click: bool
    wheel_scroll_in_preset_list_only: bool


def build_interaction_plan(ui: AppUIState) -> InteractionPlan:
    """Build hit-test and keyboard routing from app UI state."""
    return InteractionPlan(
        buttons=tuple(ui.buttons),
        shortcut_buttons=_shortcut_buttons_for_state(ui.state),
        allows_ai_board_click=ui.state is AppState.BATTLE,
        wheel_scroll_in_preset_list_only=ui.state is AppState.NEW_GAME_SETUP,
    )


def resolve_pointer_button(plan: InteractionPlan, x: float, y: float) -> str | None:
    """Resolve left-click target button id at a design-space point."""
    for button in plan.buttons:
        if button.enabled and button.contains(x, y):
            return button.id
    return None


def resolve_key_shortcut(plan: InteractionPlan, key_name: str) -> str | None:
    """Map normalized key names to button actions."""
    return plan.shortcut_buttons.get(key_name)


def can_scroll_with_wheel(plan: InteractionPlan, x: float, y: float) -> bool:
    """Return whether wheel scrolling should be routed to controller at this point."""
    if not plan.wheel_scroll_in_preset_list_only:
        return False
    return NEW_GAME_SETUP.preset_list_rect().contains(x, y)


def _shortcut_buttons_for_state(state: AppState) -> dict[str, str]:
    if state is AppState.MAIN_MENU:
        return {"enter": "new_game"}
    if state is AppState.NEW_GAME_SETUP:
        return {"enter": "start_game", "escape": "back_main"}
    if state is AppState.PRESET_MANAGE:
        return {"enter": "create_preset", "escape": "back_main"}
    if state is AppState.PLACEMENT_EDIT:
        return {"enter": "save_preset", "escape": "back_to_presets"}
    if state is AppState.BATTLE:
        return {"escape": "back_main"}
    if state is AppState.RESULT:
        return {"enter": "play_again"}
    return {}

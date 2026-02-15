"""Engine-owned interaction routing helpers."""

from __future__ import annotations

from dataclasses import dataclass

from warships.engine.api.app_port import InteractionPlanView
from warships.engine.ui_runtime.keymap import map_key_name


@dataclass(frozen=True, slots=True)
class NonModalKeyRoute:
    """Routing result for a key/char event when no modal is open."""

    controller_key: str | None = None
    controller_char: str | None = None
    shortcut_button_id: str | None = None


def resolve_pointer_button(plan: InteractionPlanView, x: float, y: float) -> str | None:
    for button in plan.buttons:
        if button.enabled and button.contains(x, y):
            return button.id
    return None


def can_scroll_with_wheel(plan: InteractionPlanView, x: float, y: float) -> bool:
    if plan.wheel_scroll_in_new_game_list and plan.new_game_list_rect is not None:
        if plan.new_game_list_rect.contains(x, y):
            return True
    if plan.wheel_scroll_in_preset_manage_panel and plan.preset_manage_rect is not None:
        if plan.preset_manage_rect.contains(x, y):
            return True
    return False


def route_non_modal_key_event(
    event_type: str,
    value: str,
    plan: InteractionPlanView,
) -> NonModalKeyRoute:
    if event_type == "char":
        if len(value) != 1 or not value.isprintable():
            return NonModalKeyRoute()
        return NonModalKeyRoute(controller_char=value)

    if event_type != "key_down":
        return NonModalKeyRoute()

    mapped = map_key_name(value)
    if mapped is None:
        return NonModalKeyRoute()
    return NonModalKeyRoute(
        controller_key=mapped,
        shortcut_button_id=plan.shortcut_buttons.get(mapped),
    )

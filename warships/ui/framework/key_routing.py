"""Keyboard mapping and non-modal key routing helpers."""

from __future__ import annotations

from dataclasses import dataclass

from warships.ui.framework.interactions import InteractionPlan, resolve_key_shortcut


@dataclass(frozen=True, slots=True)
class NonModalKeyRoute:
    """Routing result for a key/char event when no modal is open."""

    controller_key: str | None = None
    controller_char: str | None = None
    shortcut_button_id: str | None = None


def map_key_name(key_name: str) -> str | None:
    """Normalize backend key names to app key identifiers."""
    normalized = key_name.strip().lower()
    key_map = {
        "backspace": "backspace",
        "enter": "enter",
        "return": "enter",
        "escape": "escape",
        "esc": "escape",
        "r": "r",
        "d": "d",
    }
    if normalized in key_map:
        return key_map[normalized]
    if len(normalized) == 1 and normalized.isalpha():
        return normalized
    return None


def route_non_modal_key_event(
    event_type: str,
    value: str,
    interactions: InteractionPlan,
) -> NonModalKeyRoute:
    """Route key/char events when there is no active modal."""
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
        shortcut_button_id=resolve_key_shortcut(interactions, mapped),
    )


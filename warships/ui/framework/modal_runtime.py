"""Modal runtime state and input routing helpers."""

from __future__ import annotations

from dataclasses import dataclass

from warships.ui.framework.widgets import ModalTextInputWidget, resolve_modal_pointer_target


@dataclass(slots=True)
class ModalInputState:
    """Tracks modal lifecycle and text-input focus state."""

    is_open: bool = False
    input_focused: bool = False

    def sync(self, widget: ModalTextInputWidget | None) -> None:
        """Sync state with current modal presence."""
        if widget is None:
            self.is_open = False
            self.input_focused = False
            return
        if not self.is_open:
            self.input_focused = True
        self.is_open = True


@dataclass(frozen=True, slots=True)
class ModalPointerRoute:
    """Routing result for a pointer event while modal is open."""

    swallow: bool
    button_id: str | None = None
    focus_input: bool | None = None


@dataclass(frozen=True, slots=True)
class ModalKeyRoute:
    """Routing result for a key/char event while modal is open."""

    swallow: bool
    key: str | None = None
    char: str | None = None


def route_modal_pointer_event(
    widget: ModalTextInputWidget,
    state: ModalInputState,
    x: float,
    y: float,
    button: int,
) -> ModalPointerRoute:
    """Route a pointer-down event when a modal is active."""
    if button != 1:
        return ModalPointerRoute(swallow=True)
    target = resolve_modal_pointer_target(widget, x, y)
    if target == "confirm":
        return ModalPointerRoute(swallow=True, button_id=widget.confirm_button_id)
    if target == "cancel":
        return ModalPointerRoute(swallow=True, button_id=widget.cancel_button_id)
    if target == "input":
        return ModalPointerRoute(swallow=True, focus_input=True)
    if target in {"panel", "overlay"}:
        return ModalPointerRoute(swallow=True, focus_input=False)
    return ModalPointerRoute(swallow=True, focus_input=state.input_focused)


def route_modal_key_event(
    event_type: str,
    value: str,
    mapped_key: str | None,
    state: ModalInputState,
) -> ModalKeyRoute:
    """Route key/char events when a modal is active."""
    if event_type == "char":
        if not state.input_focused:
            return ModalKeyRoute(swallow=True)
        if len(value) != 1 or not value.isprintable():
            return ModalKeyRoute(swallow=True)
        return ModalKeyRoute(swallow=True, char=value)

    if event_type != "key_down":
        return ModalKeyRoute(swallow=True)

    if mapped_key is None:
        return ModalKeyRoute(swallow=True)
    if mapped_key in {"enter", "escape"}:
        return ModalKeyRoute(swallow=True, key=mapped_key)
    if mapped_key == "backspace":
        if not state.input_focused:
            return ModalKeyRoute(swallow=True)
        return ModalKeyRoute(swallow=True, key=mapped_key)
    return ModalKeyRoute(swallow=True)


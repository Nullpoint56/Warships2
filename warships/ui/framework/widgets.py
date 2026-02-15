"""Reusable widget models and rendering helpers."""

from __future__ import annotations

from dataclasses import dataclass

from warships.app.ui_state import AppUIState
from warships.ui.board_view import Rect
from warships.ui.layout_metrics import PROMPT
from warships.ui.scene import SceneRenderer


@dataclass(frozen=True, slots=True)
class ModalTextInputWidget:
    """Modal text input widget composed from UI state and shared layout metrics."""

    title: str
    value: str
    confirm_button_id: str
    cancel_button_id: str
    overlay_rect: Rect
    panel_rect: Rect
    input_rect: Rect
    confirm_button_rect: Rect
    cancel_button_rect: Rect


def build_modal_text_input_widget(ui: AppUIState) -> ModalTextInputWidget | None:
    """Build a modal text-input widget from current UI state."""
    prompt = ui.prompt
    if prompt is None:
        return None
    return ModalTextInputWidget(
        title=prompt.title,
        value=prompt.value,
        confirm_button_id=prompt.confirm_button_id,
        cancel_button_id=prompt.cancel_button_id,
        overlay_rect=PROMPT.overlay_rect(),
        panel_rect=PROMPT.panel_rect(),
        input_rect=PROMPT.input_rect(),
        confirm_button_rect=PROMPT.confirm_button_rect(),
        cancel_button_rect=PROMPT.cancel_button_rect(),
    )


def render_modal_text_input_widget(renderer: SceneRenderer, widget: ModalTextInputWidget) -> None:
    """Render a modal text input widget."""
    renderer.add_rect(
        "prompt:overlay",
        widget.overlay_rect.x,
        widget.overlay_rect.y,
        widget.overlay_rect.w,
        widget.overlay_rect.h,
        "#000000",
        z=10.0,
    )
    renderer.add_rect(
        "prompt:panel",
        widget.panel_rect.x,
        widget.panel_rect.y,
        widget.panel_rect.w,
        widget.panel_rect.h,
        "#1f2937",
        z=10.1,
    )
    renderer.add_text(
        key="prompt:title",
        text=widget.title,
        x=widget.panel_rect.x + 30.0,
        y=widget.panel_rect.y + 34.0,
        font_size=24.0,
        color="#f9fafb",
        anchor="top-left",
        z=10.2,
    )
    renderer.add_rect(
        "prompt:input:bg",
        widget.input_rect.x,
        widget.input_rect.y,
        widget.input_rect.w,
        widget.input_rect.h,
        "#111827",
        z=10.2,
    )
    renderer.add_text(
        key="prompt:value",
        text=widget.value or "_",
        x=widget.input_rect.x + 12.0,
        y=widget.input_rect.y + widget.input_rect.h / 2.0,
        font_size=18.0,
        color="#e5e7eb",
        anchor="middle-left",
        z=10.3,
    )


def resolve_modal_pointer_target(widget: ModalTextInputWidget, x: float, y: float) -> str | None:
    """Resolve pointer target for a modal widget in design-space coordinates."""
    if widget.confirm_button_rect.contains(x, y):
        return "confirm"
    if widget.cancel_button_rect.contains(x, y):
        return "cancel"
    if widget.input_rect.contains(x, y):
        return "input"
    if widget.panel_rect.contains(x, y):
        return "panel"
    if widget.overlay_rect.contains(x, y):
        return "overlay"
    return None

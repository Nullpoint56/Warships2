"""Reusable widget models and rendering helpers."""

from __future__ import annotations

from dataclasses import dataclass

from engine.api.render import RenderAPI as Render2D
from engine.api.ui_primitives import Rect
from engine.api.ui_projection import TextFitSpec, project_text_fit
from engine.api.ui_style import (
    DEFAULT_UI_STYLE_TOKENS,
    draw_rounded_rect,
    draw_shadow_rect,
    draw_stroke_rect,
)
from warships.game.app.ui_state import AppUIState
from warships.game.ui.layout_metrics import PROMPT

TOKENS = DEFAULT_UI_STYLE_TOKENS


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


def render_modal_text_input_widget(renderer: Render2D, widget: ModalTextInputWidget) -> None:
    """Render a modal text input widget."""
    renderer.add_rect(
        "prompt:overlay",
        widget.overlay_rect.x,
        widget.overlay_rect.y,
        widget.overlay_rect.w,
        widget.overlay_rect.h,
        TOKENS.shadow_strong,
        z=10.0,
    )
    draw_shadow_rect(
        renderer,
        key="prompt:panel:shadow",
        x=widget.panel_rect.x + 2.0,
        y=widget.panel_rect.y + 2.0,
        w=widget.panel_rect.w,
        h=widget.panel_rect.h,
        color=TOKENS.shadow_strong,
        z=10.05,
    )
    draw_rounded_rect(
        renderer,
        key="prompt:panel",
        x=widget.panel_rect.x,
        y=widget.panel_rect.y,
        w=widget.panel_rect.w,
        h=widget.panel_rect.h,
        radius=10.0,
        color=TOKENS.surface_elevated,
        z=10.1,
    )
    draw_stroke_rect(
        renderer,
        key="prompt:panel:border",
        x=widget.panel_rect.x,
        y=widget.panel_rect.y,
        w=widget.panel_rect.w,
        h=widget.panel_rect.h,
        color=TOKENS.border_subtle,
        z=10.11,
    )
    title_text, title_font_size, _ = project_text_fit(
        TextFitSpec(
            text=widget.title,
            rect=Rect(
                widget.panel_rect.x + 30.0,
                widget.panel_rect.y + 34.0,
                widget.panel_rect.w - 60.0,
                28.0,
            ),
            base_font_size=24.0,
            min_font_size=14.0,
            overflow_policy="ellipsis",
            parent=widget.panel_rect,
            enforce_parent=True,
        )
    )
    renderer.add_text(
        key="prompt:title",
        text=title_text,
        x=widget.panel_rect.x + 30.0,
        y=widget.panel_rect.y + 34.0,
        font_size=title_font_size,
        color=TOKENS.text_primary,
        anchor="top-left",
        z=10.2,
    )
    draw_rounded_rect(
        renderer,
        key="prompt:input:bg",
        x=widget.input_rect.x,
        y=widget.input_rect.y,
        w=widget.input_rect.w,
        h=widget.input_rect.h,
        radius=6.0,
        color=TOKENS.surface_overlay,
        z=10.2,
    )
    draw_stroke_rect(
        renderer,
        key="prompt:input:border",
        x=widget.input_rect.x,
        y=widget.input_rect.y,
        w=widget.input_rect.w,
        h=widget.input_rect.h,
        color=TOKENS.border_subtle,
        z=10.21,
    )
    value_text, value_font_size, _ = project_text_fit(
        TextFitSpec(
            text=widget.value or "_",
            rect=Rect(
                widget.input_rect.x + 8.0,
                widget.input_rect.y,
                widget.input_rect.w - 16.0,
                widget.input_rect.h,
            ),
            base_font_size=18.0,
            min_font_size=12.0,
            overflow_policy="ellipsis",
            parent=widget.input_rect,
            enforce_parent=True,
        )
    )
    renderer.add_text(
        key="prompt:value",
        text=value_text,
        x=widget.input_rect.x + 12.0,
        y=widget.input_rect.y + widget.input_rect.h / 2.0,
        font_size=value_font_size,
        color=TOKENS.text_primary,
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

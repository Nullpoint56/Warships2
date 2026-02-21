"""Generic UI projection helpers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from engine.api.ui_primitives import (
    Button,
    Rect,
    TextOverflowPolicy,
    clamp_child_rect_to_parent,
    fit_text_to_rect,
)


@dataclass(frozen=True, slots=True)
class ButtonSpec:
    """Declarative button projection spec."""

    id: str
    x: float
    y: float
    w: float
    h: float
    visible: bool = True
    enabled: bool = True
    when: bool = True


@dataclass(frozen=True, slots=True)
class TextFitSpec:
    """Declarative one-line text fit spec with optional parent constraints."""

    text: str
    rect: Rect
    base_font_size: float
    min_font_size: float = 8.0
    pad_x: float = 10.0
    pad_y: float = 6.0
    overflow_policy: TextOverflowPolicy = "ellipsis"
    parent: Rect | None = None
    enforce_parent: bool = False


def project_buttons(
    specs: Sequence[ButtonSpec],
    *,
    container: Rect | None = None,
    clamp_to_container: bool = False,
    pad_x: float = 0.0,
    pad_y: float = 0.0,
) -> list[Button]:
    """Project declarative specs into concrete button primitives."""
    def _project(spec: ButtonSpec) -> Button:
        rect = Rect(spec.x, spec.y, spec.w, spec.h)
        if clamp_to_container and container is not None:
            rect = clamp_child_rect_to_parent(rect, container, pad_x=pad_x, pad_y=pad_y)
        return Button(
            id=spec.id,
            x=rect.x,
            y=rect.y,
            w=rect.w,
            h=rect.h,
            visible=spec.visible,
            enabled=spec.enabled,
        )
    return [
        _project(spec)
        for spec in specs
        if spec.when
    ]


def project_text_fit(spec: TextFitSpec) -> tuple[str, float, Rect]:
    """Project fitted one-line text and effective rect using shared policies."""
    rect = spec.rect
    if spec.enforce_parent and spec.parent is not None:
        rect = clamp_child_rect_to_parent(rect, spec.parent, pad_x=0.0, pad_y=0.0)
    text, size = fit_text_to_rect(
        spec.text,
        rect_w=rect.w,
        rect_h=rect.h,
        base_font_size=spec.base_font_size,
        min_font_size=spec.min_font_size,
        pad_x=spec.pad_x,
        pad_y=spec.pad_y,
        overflow_policy=spec.overflow_policy,
    )
    return text, size, rect

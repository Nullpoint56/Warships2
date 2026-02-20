"""Generic UI projection helpers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from engine.api.ui_primitives import Button, Rect, clamp_child_rect_to_parent


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

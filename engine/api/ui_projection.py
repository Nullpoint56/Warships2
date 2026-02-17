"""Generic UI projection helpers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from engine.api.ui_primitives import Button


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


def project_buttons(specs: Sequence[ButtonSpec]) -> list[Button]:
    """Project declarative specs into concrete button primitives."""
    return [
        Button(
            id=spec.id,
            x=spec.x,
            y=spec.y,
            w=spec.w,
            h=spec.h,
            visible=spec.visible,
            enabled=spec.enabled,
        )
        for spec in specs
        if spec.when
    ]

"""Engine-owned basic UI widget primitives."""

from __future__ import annotations

from dataclasses import dataclass

from engine.api.ui_primitives import ButtonStyle


@dataclass(frozen=True, slots=True)
class Button:
    """Clickable rectangular button primitive."""

    id: str
    x: float
    y: float
    w: float
    h: float
    visible: bool = True
    enabled: bool = True
    style: ButtonStyle | dict[str, object] | None = None

    def contains(self, px: float, py: float) -> bool:
        """Return whether this button contains the point."""
        return self.visible and self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h

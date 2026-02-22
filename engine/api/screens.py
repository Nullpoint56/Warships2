"""Public screen-stack API contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

LayerKind = Literal["root", "overlay"]


class ScreenData(Protocol):
    """Opaque screen payload boundary contract."""


@dataclass(frozen=True, slots=True)
class ScreenLayer:
    """Public screen layer shape."""

    screen_id: str
    kind: LayerKind
    data: ScreenData | None = None


class ScreenStack(Protocol):
    """Public screen stack contract."""

    def set_root(self, screen_id: str, *, data: ScreenData | None = None) -> ScreenLayer:
        """Replace root and clear overlays."""

    def push_overlay(self, screen_id: str, *, data: ScreenData | None = None) -> ScreenLayer:
        """Push one overlay."""

    def pop_overlay(self) -> ScreenLayer | None:
        """Pop top overlay."""

    def clear_overlays(self) -> None:
        """Clear overlays."""

    def root(self) -> ScreenLayer | None:
        """Return root."""

    def top(self) -> ScreenLayer | None:
        """Return top visible."""

    def layers(self) -> tuple[ScreenLayer, ...]:
        """Return root-first snapshot."""

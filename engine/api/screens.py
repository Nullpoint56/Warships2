"""Public screen-stack API contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

LayerKind = Literal["root", "overlay"]


class ScreenData(Protocol):
    """Opaque screen payload boundary contract."""


@dataclass(frozen=True, slots=True)
class ScreenLayer:
    """Public screen layer shape."""

    screen_id: str
    kind: LayerKind
    data: ScreenData | None = None


class ScreenStack(ABC):
    """Public screen stack contract."""

    @abstractmethod
    def set_root(self, screen_id: str, *, data: ScreenData | None = None) -> ScreenLayer:
        """Replace root and clear overlays."""

    @abstractmethod
    def push_overlay(self, screen_id: str, *, data: ScreenData | None = None) -> ScreenLayer:
        """Push one overlay."""

    @abstractmethod
    def pop_overlay(self) -> ScreenLayer | None:
        """Pop top overlay."""

    @abstractmethod
    def clear_overlays(self) -> None:
        """Clear overlays."""

    @abstractmethod
    def root(self) -> ScreenLayer | None:
        """Return root."""

    @abstractmethod
    def top(self) -> ScreenLayer | None:
        """Return top visible."""

    @abstractmethod
    def layers(self) -> tuple[ScreenLayer, ...]:
        """Return root-first snapshot."""

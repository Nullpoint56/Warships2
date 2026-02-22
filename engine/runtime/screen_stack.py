"""Screen stack primitives for runtime composition."""

from __future__ import annotations

from engine.api.screens import ScreenData, ScreenLayer


class RuntimeScreenStack:
    """Layered root + overlay screen stack."""

    def __init__(self) -> None:
        self._root: ScreenLayer | None = None
        self._overlays: list[ScreenLayer] = []

    def set_root(self, screen_id: str, *, data: ScreenData | None = None) -> ScreenLayer:
        """Replace root screen and clear overlays."""
        layer = ScreenLayer(screen_id=screen_id, kind="root", data=data)
        self._root = layer
        self._overlays.clear()
        return layer

    def push_overlay(self, screen_id: str, *, data: ScreenData | None = None) -> ScreenLayer:
        """Push an overlay layer above root."""
        if self._root is None:
            raise RuntimeError("cannot push overlay without root screen")
        layer = ScreenLayer(screen_id=screen_id, kind="overlay", data=data)
        self._overlays.append(layer)
        return layer

    def pop_overlay(self) -> ScreenLayer | None:
        """Pop topmost overlay layer."""
        if not self._overlays:
            return None
        return self._overlays.pop()

    def clear_overlays(self) -> None:
        """Remove all overlay layers."""
        self._overlays.clear()

    def root(self) -> ScreenLayer | None:
        """Return current root layer."""
        return self._root

    def top(self) -> ScreenLayer | None:
        """Return topmost visible layer."""
        if self._overlays:
            return self._overlays[-1]
        return self._root

    def layers(self) -> tuple[ScreenLayer, ...]:
        """Return root-first layer snapshot."""
        if self._root is None:
            return tuple(self._overlays)
        return (self._root, *self._overlays)


ScreenStack = RuntimeScreenStack

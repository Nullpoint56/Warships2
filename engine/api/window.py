"""Window and surface contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from engine.api.input_events import KeyEvent, PointerEvent, WheelEvent


@dataclass(frozen=True, slots=True)
class SurfaceHandle:
    """Opaque renderer-attachable surface handle."""

    surface_id: str
    backend: str
    provider: object | None = None


@dataclass(frozen=True, slots=True)
class WindowResizeEvent:
    """Normalized resize/DPI event in logical and physical units."""

    logical_width: float
    logical_height: float
    physical_width: int
    physical_height: int
    dpi_scale: float


@dataclass(frozen=True, slots=True)
class WindowFocusEvent:
    """Normalized focus event."""

    focused: bool


@dataclass(frozen=True, slots=True)
class WindowMinimizeEvent:
    """Normalized minimize/restore event."""

    minimized: bool


@dataclass(frozen=True, slots=True)
class WindowCloseEvent:
    """Normalized close-request event."""

    requested: bool = True


WindowEvent = WindowResizeEvent | WindowFocusEvent | WindowMinimizeEvent | WindowCloseEvent


class WindowPort(Protocol):
    """Engine-facing window/event-loop ownership contract."""

    def create_surface(self) -> SurfaceHandle:
        """Create a surface handle used by the renderer backend."""

    def poll_events(self) -> tuple[WindowEvent, ...]:
        """Poll and return normalized window events."""

    def poll_input_events(self) -> tuple[PointerEvent | KeyEvent | WheelEvent, ...]:
        """Poll and return normalized raw input events for input subsystem ingestion."""

    def set_title(self, title: str) -> None:
        """Set OS window title."""

    def set_windowed(self, width: int, height: int) -> None:
        """Configure windowed mode with logical size."""

    def set_fullscreen(self) -> None:
        """Configure fullscreen mode."""

    def set_maximized(self) -> None:
        """Configure maximized mode."""

    def run_loop(self) -> None:
        """Run the OS/backend event loop."""

    def stop_loop(self) -> None:
        """Stop the OS/backend event loop when supported."""

    def close(self) -> None:
        """Close window and release backend resources."""


__all__ = [
    "SurfaceHandle",
    "WindowCloseEvent",
    "WindowEvent",
    "WindowFocusEvent",
    "WindowMinimizeEvent",
    "WindowPort",
    "WindowResizeEvent",
]

"""Engine-owned rendering API contract."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol


class RenderAPI(Protocol):
    """Rendering capabilities exposed by the engine to higher layers."""

    def begin_frame(self) -> None:
        """Prepare frame-local renderer state."""

    def end_frame(self) -> None:
        """Finalize frame-local renderer state."""

    def add_rect(
        self,
        key: str | None,
        x: float,
        y: float,
        w: float,
        h: float,
        color: str,
        z: float = 0.0,
        static: bool = False,
    ) -> None:
        """Draw or update a rectangle primitive."""

    def add_grid(
        self,
        key: str,
        x: float,
        y: float,
        width: float,
        height: float,
        lines: int,
        color: str,
        z: float = 0.5,
        static: bool = False,
    ) -> None:
        """Draw or update a grid primitive."""

    def add_text(
        self,
        key: str | None,
        text: str,
        x: float,
        y: float,
        font_size: float = 18.0,
        color: str = "#ffffff",
        anchor: str = "top-left",
        z: float = 2.0,
        static: bool = False,
    ) -> None:
        """Draw or update a text primitive."""

    def set_title(self, title: str) -> None:
        """Set window title when supported."""

    def fill_window(self, key: str, color: str, z: float = -100.0) -> None:
        """Fill the full window area regardless of design-space/aspect transform."""

    def to_design_space(self, x: float, y: float) -> tuple[float, float]:
        """Map pointer coordinates into design-space coordinates."""

    def invalidate(self) -> None:
        """Schedule one redraw."""

    def run(self, draw_callback: Callable[[], None]) -> None:
        """Run render loop with callback-driven frames."""

    def close(self) -> None:
        """Close renderer resources and stop the loop."""

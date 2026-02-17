"""Engine-owned grid layout and hit-testing helpers."""

from __future__ import annotations

from dataclasses import dataclass

from engine.ui_runtime.geometry import CellCoord, Rect


@dataclass(frozen=True, slots=True)
class GridLayout:
    """Layout and hit-testing helpers for a two-surface cell grid."""

    primary_origin_x: float = 80.0
    secondary_origin_x: float = 640.0
    origin_y: float = 150.0
    cell_size: float = 42.0
    grid_size: int = 10

    def _origin_x_for_target(self, grid_target: str) -> float:
        normalized = grid_target.strip().lower()
        if normalized == "secondary":
            return self.secondary_origin_x
        if normalized == "primary":
            return self.primary_origin_x
        raise ValueError(f"unknown grid target: {grid_target!r}")

    def rect_for_target(self, grid_target: str) -> Rect:
        """Return rectangle for a named grid target."""
        size_px = self.grid_size * self.cell_size
        return Rect(self._origin_x_for_target(grid_target), self.origin_y, size_px, size_px)

    def cell_rect_for_target(self, grid_target: str, row: int, col: int) -> Rect:
        """Return pixel rectangle for a grid cell."""
        origin_x = self._origin_x_for_target(grid_target)
        return Rect(
            x=origin_x + col * self.cell_size,
            y=self.origin_y + row * self.cell_size,
            w=self.cell_size,
            h=self.cell_size,
        )

    def screen_to_cell(self, grid_target: str, px: float, py: float) -> CellCoord | None:
        """Convert screen point to cell coordinate for a named grid target."""
        rect = self.rect_for_target(grid_target)
        if not rect.contains(px, py):
            return None
        col = int((px - rect.x) // self.cell_size)
        row = int((py - rect.y) // self.cell_size)
        if not (0 <= row < self.grid_size and 0 <= col < self.grid_size):
            return None
        return CellCoord(row=row, col=col)

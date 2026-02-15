"""Engine-owned board layout and hit-testing helpers."""

from __future__ import annotations

from dataclasses import dataclass

from warships.core.models import BOARD_SIZE, Coord


@dataclass(frozen=True, slots=True)
class Rect:
    """Simple axis-aligned rectangle."""

    x: float
    y: float
    w: float
    h: float

    def contains(self, px: float, py: float) -> bool:
        """Return whether a point is inside the rectangle."""
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h


@dataclass(frozen=True, slots=True)
class BoardLayout:
    """Board layout and hit-testing helpers."""

    player_origin_x: float = 80.0
    ai_origin_x: float = 640.0
    origin_y: float = 150.0
    cell_size: float = 42.0
    board_size: int = BOARD_SIZE

    def board_rect(self, is_ai: bool) -> Rect:
        """Return board rect for player or AI side."""
        x = self.ai_origin_x if is_ai else self.player_origin_x
        size_px = self.board_size * self.cell_size
        return Rect(x, self.origin_y, size_px, size_px)

    def cell_rect(self, is_ai: bool, coord: Coord) -> Rect:
        """Return pixel rectangle for a board cell."""
        origin_x = self.ai_origin_x if is_ai else self.player_origin_x
        return Rect(
            x=origin_x + coord.col * self.cell_size,
            y=self.origin_y + coord.row * self.cell_size,
            w=self.cell_size,
            h=self.cell_size,
        )

    def screen_to_cell(self, is_ai: bool, px: float, py: float) -> Coord | None:
        """Convert screen point to board coordinate."""
        rect = self.board_rect(is_ai)
        if not rect.contains(px, py):
            return None
        col = int((px - rect.x) // self.cell_size)
        row = int((py - rect.y) // self.cell_size)
        if not (0 <= row < self.board_size and 0 <= col < self.board_size):
            return None
        return Coord(row=row, col=col)


"""Hunt/Target AI strategy implementation for V1."""

from __future__ import annotations

import random
from collections import deque

from warships.game.ai.strategy import AIStrategy
from warships.game.core.models import BOARD_SIZE, Coord, ShotResult


class HuntTargetAI(AIStrategy):
    """Deterministic hunt/target AI with parity optimization."""

    def __init__(self, rng: random.Random, size: int = BOARD_SIZE) -> None:
        self._rng = rng
        self._size = size
        self._remaining: set[tuple[int, int]] = {(r, c) for r in range(size) for c in range(size)}
        self._target_queue: deque[Coord] = deque()
        self._active_hits: list[Coord] = []
        self._hunt_cells: list[Coord] = [
            Coord(r, c) for r in range(size) for c in range(size) if (r + c) % 2 == 0
        ]
        self._rng.shuffle(self._hunt_cells)

    def choose_shot(self) -> Coord:
        while self._target_queue:
            coord = self._target_queue.popleft()
            if (coord.row, coord.col) in self._remaining:
                return coord

        while self._hunt_cells:
            coord = self._hunt_cells.pop()
            if (coord.row, coord.col) in self._remaining:
                return coord

        row, col = self._rng.choice(list(self._remaining))
        return Coord(row, col)

    def notify_result(self, coord: Coord, result: ShotResult) -> None:
        self._remaining.discard((coord.row, coord.col))

        if result is ShotResult.HIT:
            self._active_hits.append(coord)
            self._enqueue_target_neighbors(coord)
            self._narrow_queue_by_orientation()
        elif result is ShotResult.SUNK:
            self._active_hits.clear()
            self._target_queue.clear()

    def _enqueue_target_neighbors(self, coord: Coord) -> None:
        candidates = (
            Coord(coord.row - 1, coord.col),
            Coord(coord.row + 1, coord.col),
            Coord(coord.row, coord.col - 1),
            Coord(coord.row, coord.col + 1),
        )
        for cell in candidates:
            if not (0 <= cell.row < self._size and 0 <= cell.col < self._size):
                continue
            if (cell.row, cell.col) not in self._remaining:
                continue
            self._target_queue.append(cell)

    def _narrow_queue_by_orientation(self) -> None:
        if len(self._active_hits) < 2:
            return

        rows = {coord.row for coord in self._active_hits}
        cols = {coord.col for coord in self._active_hits}
        if len(rows) == 1:
            row = next(iter(rows))
            self._target_queue = deque(coord for coord in self._target_queue if coord.row == row)
        elif len(cols) == 1:
            col = next(iter(cols))
            self._target_queue = deque(coord for coord in self._target_queue if coord.col == col)


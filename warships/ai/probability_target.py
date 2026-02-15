"""Probability-density AI with constrained target mode for harder gameplay."""

from __future__ import annotations

import random

from warships.ai.strategy import AIStrategy
from warships.core.models import BOARD_SIZE, Coord, ShotResult


class ProbabilityTargetAI(AIStrategy):
    """Hard AI that scores cells from all valid ship placements."""

    def __init__(self, rng: random.Random, size: int = BOARD_SIZE) -> None:
        self._rng = rng
        self._size = size
        self._remaining: set[tuple[int, int]] = {(r, c) for r in range(size) for c in range(size)}
        self._misses: set[tuple[int, int]] = set()
        self._active_hits: list[Coord] = []
        self._remaining_ship_lengths: list[int] = [5, 4, 3, 3, 2]

    def choose_shot(self) -> Coord:
        required_hits = set((c.row, c.col) for c in self._active_hits)
        scores = self._build_scores(required_hits)
        if not scores:
            row, col = self._rng.choice(list(self._remaining))
            return Coord(row=row, col=col)

        max_score = max(scores.values())
        candidates = [Coord(r, c) for (r, c), score in scores.items() if score == max_score]
        return self._rng.choice(candidates)

    def notify_result(self, coord: Coord, result: ShotResult) -> None:
        key = (coord.row, coord.col)
        self._remaining.discard(key)

        if result is ShotResult.MISS:
            self._misses.add(key)
            return

        if result is ShotResult.HIT:
            self._record_hit(coord)
            return

        if result is ShotResult.SUNK:
            self._record_hit(coord)
            self._consume_ship_length(len(self._active_hits))
            self._active_hits.clear()

    def _record_hit(self, coord: Coord) -> None:
        if not self._active_hits:
            self._active_hits.append(coord)
            return
        if any(_is_adjacent(coord, existing) for existing in self._active_hits):
            if coord not in self._active_hits:
                self._active_hits.append(coord)
            return
        # If we somehow drifted to a disjoint cluster, prioritize the freshest hit.
        self._active_hits = [coord]

    def _consume_ship_length(self, length: int) -> None:
        if length in self._remaining_ship_lengths:
            self._remaining_ship_lengths.remove(length)
            return
        if self._remaining_ship_lengths:
            # Fallback for ambiguous sink clusters: remove the longest remaining ship.
            self._remaining_ship_lengths.remove(max(self._remaining_ship_lengths))

    def _build_scores(self, required_hits: set[tuple[int, int]]) -> dict[tuple[int, int], int]:
        scores: dict[tuple[int, int], int] = {}
        for ship_len in self._remaining_ship_lengths:
            self._accumulate_ship_length_scores(ship_len, required_hits, scores)
        return scores

    def _accumulate_ship_length_scores(
        self,
        ship_len: int,
        required_hits: set[tuple[int, int]],
        scores: dict[tuple[int, int], int],
    ) -> None:
        for row in range(self._size):
            for col in range(self._size - ship_len + 1):
                cells = [(row, col + offset) for offset in range(ship_len)]
                self._accumulate_if_valid(cells, required_hits, scores)
        for row in range(self._size - ship_len + 1):
            for col in range(self._size):
                cells = [(row + offset, col) for offset in range(ship_len)]
                self._accumulate_if_valid(cells, required_hits, scores)

    def _accumulate_if_valid(
        self,
        cells: list[tuple[int, int]],
        required_hits: set[tuple[int, int]],
        scores: dict[tuple[int, int], int],
    ) -> None:
        cells_set = set(cells)
        if required_hits and not required_hits.issubset(cells_set):
            return
        for cell in cells:
            if cell in self._misses:
                return
            if cell not in self._remaining and cell not in required_hits:
                return
        for cell in cells:
            if cell in self._remaining:
                scores[cell] = scores.get(cell, 0) + 1


def _is_adjacent(a: Coord, b: Coord) -> bool:
    return abs(a.row - b.row) + abs(a.col - b.col) == 1


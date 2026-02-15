"""Hard AI: hunt by ship-pattern probabilities, then finish ships deterministically."""

from __future__ import annotations

from dataclasses import dataclass
import random

from warships.ai.strategy import AIStrategy
from warships.core.models import BOARD_SIZE, Coord, ShotResult


@dataclass(slots=True)
class _HitCluster:
    hits: set[tuple[int, int]]
    last_updated: int


class PatternHardAI(AIStrategy):
    """Strong AI that aggressively converts hits into sinks."""

    def __init__(self, rng: random.Random, size: int = BOARD_SIZE) -> None:
        self._rng = rng
        self._size = size
        self._remaining: set[tuple[int, int]] = {(r, c) for r in range(size) for c in range(size)}
        self._misses: set[tuple[int, int]] = set()
        self._remaining_ship_lengths: list[int] = [5, 4, 3, 3, 2]
        self._active_clusters: list[_HitCluster] = []
        self._shot_index = 0

    def choose_shot(self) -> Coord:
        if self._active_clusters:
            for cluster in self._ordered_clusters():
                target = self._choose_cluster_target_shot(cluster)
                if target is not None:
                    return target
            # Defensive recovery: clusters became stale.
            self._active_clusters.clear()

        return self._choose_hunt_shot()

    def notify_result(self, coord: Coord, result: ShotResult) -> None:
        self._shot_index += 1
        key = (coord.row, coord.col)
        self._remaining.discard(key)

        if result is ShotResult.MISS:
            self._misses.add(key)
            return

        cluster = self._record_hit(key)
        if result is ShotResult.HIT:
            return
        if result is ShotResult.SUNK:
            self._consume_ship_length(len(cluster.hits))
            self._active_clusters = [item for item in self._active_clusters if item is not cluster]

    def _choose_cluster_target_shot(self, cluster: _HitCluster) -> Coord | None:
        orientation = self._cluster_orientation(cluster)
        if orientation is not None:
            line_candidates = self._line_extension_candidates(cluster, orientation)
            if line_candidates:
                return self._pick_best(line_candidates)

        candidates = self._adjacent_candidates(cluster)
        if candidates:
            return self._pick_best(candidates)
        return None

    def _adjacent_candidates(self, cluster: _HitCluster) -> list[Coord]:
        seen: set[tuple[int, int]] = set()
        result: list[Coord] = []
        for row, col in cluster.hits:
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                rr = row + dr
                cc = col + dc
                key = (rr, cc)
                if not (0 <= rr < self._size and 0 <= cc < self._size):
                    continue
                if key not in self._remaining or key in seen:
                    continue
                seen.add(key)
                result.append(Coord(rr, cc))
        return result

    def _line_extension_candidates(self, cluster: _HitCluster, orientation: str) -> list[Coord]:
        if orientation == "H":
            row = next(iter(cluster.hits))[0]
            min_col = min(col for _, col in cluster.hits)
            max_col = max(col for _, col in cluster.hits)
            return self._remaining_coords([(row, min_col - 1), (row, max_col + 1)])

        col = next(iter(cluster.hits))[1]
        min_row = min(row for row, _ in cluster.hits)
        max_row = max(row for row, _ in cluster.hits)
        return self._remaining_coords([(min_row - 1, col), (max_row + 1, col)])

    def _remaining_coords(self, coords: list[tuple[int, int]]) -> list[Coord]:
        result: list[Coord] = []
        for rr, cc in coords:
            if not (0 <= rr < self._size and 0 <= cc < self._size):
                continue
            if (rr, cc) in self._remaining:
                result.append(Coord(rr, cc))
        return result

    def _choose_hunt_shot(self) -> Coord:
        scores = self._hunt_scores()
        if not scores:
            row, col = self._rng.choice(list(self._remaining))
            return Coord(row=row, col=col)

        best_score = max(scores.values())
        best = [Coord(r, c) for (r, c), score in scores.items() if score == best_score]
        # Prefer parity while no ship of size 1 exists.
        if self._remaining_ship_lengths and min(self._remaining_ship_lengths) > 1:
            parity = [coord for coord in best if (coord.row + coord.col) % 2 == 0]
            if parity:
                best = parity
        return self._rng.choice(best)

    def _hunt_scores(self) -> dict[tuple[int, int], float]:
        scores: dict[tuple[int, int], float] = {}
        for ship_len in self._remaining_ship_lengths:
            self._accumulate_scores_for_length(ship_len, scores)
        return scores

    def _accumulate_scores_for_length(self, ship_len: int, scores: dict[tuple[int, int], float]) -> None:
        placements: list[list[tuple[int, int]]] = []
        for row in range(self._size):
            for col in range(self._size - ship_len + 1):
                cells = [(row, col + i) for i in range(ship_len)]
                if self._is_valid_placement(cells):
                    placements.append(cells)

        for row in range(self._size - ship_len + 1):
            for col in range(self._size):
                cells = [(row + i, col) for i in range(ship_len)]
                if self._is_valid_placement(cells):
                    placements.append(cells)

        if not placements:
            return
        # Scarce placements get amplified so late-game search locks onto legal gaps.
        scarcity_weight = (self._size * self._size) / len(placements)
        placement_weight = ship_len * scarcity_weight
        for cells in placements:
            for cell in cells:
                scores[cell] = scores.get(cell, 0.0) + placement_weight

    def _is_valid_placement(self, cells: list[tuple[int, int]]) -> bool:
        for cell in cells:
            if cell in self._misses:
                return False
            if cell not in self._remaining:
                return False
        return True

    def _record_hit(self, hit: tuple[int, int]) -> _HitCluster:
        touching = [cluster for cluster in self._active_clusters if self._touches_cluster(hit, cluster)]
        if not touching:
            cluster = _HitCluster(hits={hit}, last_updated=self._shot_index)
            self._active_clusters.append(cluster)
            return cluster

        cluster = touching[0]
        cluster.hits.add(hit)
        cluster.last_updated = self._shot_index

        if len(touching) > 1:
            for extra in touching[1:]:
                cluster.hits.update(extra.hits)
                cluster.last_updated = max(cluster.last_updated, extra.last_updated)
                self._active_clusters.remove(extra)
        return cluster

    @staticmethod
    def _touches_cluster(hit: tuple[int, int], cluster: _HitCluster) -> bool:
        row, col = hit
        for rr, cc in cluster.hits:
            if abs(rr - row) + abs(cc - col) == 1:
                return True
        return False

    @staticmethod
    def _cluster_orientation(cluster: _HitCluster) -> str | None:
        if len(cluster.hits) < 2:
            return None
        rows = {row for row, _ in cluster.hits}
        cols = {col for _, col in cluster.hits}
        if len(rows) == 1:
            return "H"
        if len(cols) == 1:
            return "V"
        return None

    def _ordered_clusters(self) -> list[_HitCluster]:
        return sorted(self._active_clusters, key=lambda c: (len(c.hits), c.last_updated), reverse=True)

    def _consume_ship_length(self, length: int) -> None:
        if length in self._remaining_ship_lengths:
            self._remaining_ship_lengths.remove(length)
            return
        if not self._remaining_ship_lengths:
            return
        # Defensive fallback if hit tracking drifted: remove closest size.
        closest = min(self._remaining_ship_lengths, key=lambda s: abs(s - length))
        self._remaining_ship_lengths.remove(closest)

    def _pick_best(self, coords: list[Coord]) -> Coord:
        if len(coords) == 1:
            return coords[0]
        score_map = self._hunt_scores()
        best_score = max(score_map.get((c.row, c.col), 0) for c in coords)
        best = [c for c in coords if score_map.get((c.row, c.col), 0) == best_score]
        return self._rng.choice(best)

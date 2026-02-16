"""AI scoring helpers."""

from __future__ import annotations


def normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    """Normalize non-negative scores to probabilities."""
    if not scores:
        return {}
    clamped = {action: max(0.0, value) for action, value in scores.items()}
    total = sum(clamped.values())
    if total == 0.0:
        uniform = 1.0 / len(clamped)
        return {action: uniform for action in clamped}
    return {action: value / total for action, value in clamped.items()}


def best_action(scores: dict[str, float]) -> str | None:
    """Return highest-scoring action with stable tie-breaker."""
    if not scores:
        return None
    return max(sorted(scores), key=lambda action: scores[action])


def combine_weighted_scores(
    weighted_scores: tuple[tuple[dict[str, float], float], ...],
) -> dict[str, float]:
    """Combine multiple weighted score maps by summation."""
    combined: dict[str, float] = {}
    for score_map, weight in weighted_scores:
        if weight == 0.0:
            continue
        for action, score in score_map.items():
            combined[action] = combined.get(action, 0.0) + (score * weight)
    return combined

from __future__ import annotations

from engine.api.ai import best_action, combine_weighted_scores, normalize_scores


def test_normalize_scores_handles_empty_and_uniform() -> None:
    assert normalize_scores({}) == {}
    uniform = normalize_scores({"a": 0.0, "b": -1.0})
    assert uniform == {"a": 0.5, "b": 0.5}


def test_normalize_scores_produces_probability_distribution() -> None:
    normalized = normalize_scores({"a": 1.0, "b": 3.0})
    assert normalized["a"] == 0.25
    assert normalized["b"] == 0.75


def test_best_action_and_weighted_combine() -> None:
    assert best_action({}) is None
    assert best_action({"a": 1.0, "b": 2.0}) == "b"
    combined = combine_weighted_scores(
        (
            ({"a": 1.0, "b": 2.0}, 0.5),
            ({"a": 2.0, "c": 4.0}, 1.0),
        )
    )
    assert combined == {"a": 2.5, "b": 1.0, "c": 4.0}

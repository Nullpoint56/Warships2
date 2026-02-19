from __future__ import annotations

from pathlib import Path

from engine.api.debug import ReplayValidationView
from tools.engine_repro_lab.diff import (
    compare_batch_runs,
    compare_validation_runs,
    find_first_divergence,
)
from tools.engine_repro_lab.runner import ValidationConfig, ValidationRun


def _run(path: str, *, passed: bool, mismatches: list[dict]) -> ValidationRun:
    return ValidationRun(
        replay_path=Path(path),
        config=ValidationConfig(),
        result=ReplayValidationView(
            schema_version="diag.replay_validation.v1",
            passed=passed,
            total_ticks=20,
            commands_applied=8,
            checkpoint_count=5,
            mismatches=mismatches,
        ),
    )


def test_find_first_divergence() -> None:
    divergence = find_first_divergence(
        [
            {"tick": 7, "expected_hash": "a", "actual_hash": "b"},
            {"tick": 3, "expected_hash": "c", "actual_hash": "d"},
        ]
    )
    assert divergence is not None
    assert divergence.tick == 3
    assert divergence.expected_hash == "c"
    assert divergence.actual_hash == "d"


def test_compare_validation_runs_uses_candidate_first_divergence() -> None:
    baseline = _run("replay.json", passed=True, mismatches=[])
    candidate = _run(
        "replay.json",
        passed=False,
        mismatches=[{"tick": 5, "expected_hash": "x", "actual_hash": "y"}],
    )
    diff = compare_validation_runs(baseline, candidate)
    assert diff.replay_path.endswith("replay.json")
    assert diff.baseline_passed is True
    assert diff.candidate_passed is False
    assert diff.mismatch_delta == 1
    assert diff.first_divergence is not None
    assert diff.first_divergence.tick == 5


def test_compare_batch_runs_summary_and_missing_sets() -> None:
    baseline_runs = [
        _run("a.json", passed=True, mismatches=[]),
        _run(
            "b.json",
            passed=False,
            mismatches=[{"tick": 1, "expected_hash": "a", "actual_hash": "b"}],
        ),
    ]
    candidate_runs = [
        _run(
            "a.json",
            passed=False,
            mismatches=[{"tick": 2, "expected_hash": "c", "actual_hash": "d"}],
        ),
        _run("c.json", passed=True, mismatches=[]),
    ]
    diffs, summary = compare_batch_runs(baseline_runs, candidate_runs)

    assert len(diffs) == 1
    assert diffs[0].replay_path.endswith("a.json")
    assert summary.total_compared == 1
    assert summary.regressions == 1
    assert summary.improvements == 0
    assert summary.unchanged == 0
    assert any(path.endswith("b.json") for path in summary.missing_in_candidate)
    assert any(path.endswith("c.json") for path in summary.missing_in_baseline)

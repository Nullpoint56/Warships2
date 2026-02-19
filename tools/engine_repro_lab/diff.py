"""Differential replay validation helpers (baseline vs candidate)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from tools.engine_repro_lab.runner import ValidationRun


@dataclass(frozen=True)
class FirstDivergence:
    tick: int
    expected_hash: str
    actual_hash: str


@dataclass(frozen=True)
class DifferentialResult:
    replay_path: str
    baseline_passed: bool
    candidate_passed: bool
    baseline_mismatch_count: int
    candidate_mismatch_count: int
    mismatch_delta: int
    first_divergence: FirstDivergence | None


@dataclass(frozen=True)
class BatchDifferentialSummary:
    total_compared: int
    regressions: int
    improvements: int
    unchanged: int
    missing_in_candidate: list[str]
    missing_in_baseline: list[str]


def find_first_divergence(mismatches: Iterable[dict]) -> FirstDivergence | None:
    items = [item for item in mismatches if isinstance(item, dict)]
    if not items:
        return None
    best = min(items, key=lambda item: int(item.get("tick", 0)))
    return FirstDivergence(
        tick=int(best.get("tick", 0)),
        expected_hash=str(best.get("expected_hash", "")),
        actual_hash=str(best.get("actual_hash", "")),
    )


def compare_validation_runs(
    baseline: ValidationRun,
    candidate: ValidationRun,
) -> DifferentialResult:
    base_mismatches = list(baseline.result.mismatches)
    cand_mismatches = list(candidate.result.mismatches)
    candidate_first = find_first_divergence(cand_mismatches)
    baseline_first = find_first_divergence(base_mismatches)
    first = candidate_first if candidate_first is not None else baseline_first
    return DifferentialResult(
        replay_path=str(candidate.replay_path),
        baseline_passed=bool(baseline.result.passed),
        candidate_passed=bool(candidate.result.passed),
        baseline_mismatch_count=len(base_mismatches),
        candidate_mismatch_count=len(cand_mismatches),
        mismatch_delta=len(cand_mismatches) - len(base_mismatches),
        first_divergence=first,
    )


def compare_batch_runs(
    baseline_runs: Iterable[ValidationRun],
    candidate_runs: Iterable[ValidationRun],
) -> tuple[list[DifferentialResult], BatchDifferentialSummary]:
    baseline_map = {str(run.replay_path): run for run in baseline_runs}
    candidate_map = {str(run.replay_path): run for run in candidate_runs}

    compared: list[DifferentialResult] = []
    regressions = 0
    improvements = 0
    unchanged = 0

    for replay_path in sorted(set(baseline_map).intersection(candidate_map)):
        diff = compare_validation_runs(baseline_map[replay_path], candidate_map[replay_path])
        compared.append(diff)
        if diff.mismatch_delta > 0 or (diff.baseline_passed and not diff.candidate_passed):
            regressions += 1
        elif diff.mismatch_delta < 0 or (not diff.baseline_passed and diff.candidate_passed):
            improvements += 1
        else:
            unchanged += 1

    missing_in_candidate = sorted(set(baseline_map) - set(candidate_map))
    missing_in_baseline = sorted(set(candidate_map) - set(baseline_map))
    summary = BatchDifferentialSummary(
        total_compared=len(compared),
        regressions=regressions,
        improvements=improvements,
        unchanged=unchanged,
        missing_in_candidate=missing_in_candidate,
        missing_in_baseline=missing_in_baseline,
    )
    return compared, summary

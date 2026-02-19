"""Batch replay validation helpers for CI-style reproducibility checks."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.engine_repro_lab.runner import ValidationConfig, ValidationRun, run_validation_from_file

SimulatorFactory = Callable[[], tuple[Any, Any]]


@dataclass(frozen=True)
class BatchValidationSummary:
    total_replays: int
    passed_count: int
    failed_count: int
    total_mismatches: int
    worst_replay: str | None
    worst_mismatch_count: int


def run_batch_validation(
    replay_paths: Iterable[Path],
    *,
    config: ValidationConfig,
    simulator_factory: SimulatorFactory,
) -> list[ValidationRun]:
    runs: list[ValidationRun] = []
    for replay_path in replay_paths:
        apply_command, step = simulator_factory()
        runs.append(
            run_validation_from_file(
                replay_path,
                config=config,
                apply_command=apply_command,
                step=step,
            )
        )
    return runs


def summarize_batch_runs(runs: Iterable[ValidationRun]) -> BatchValidationSummary:
    run_list = list(runs)
    total = len(run_list)
    passed = sum(1 for run in run_list if run.result.passed)
    failed = total - passed
    mismatch_counts: list[tuple[str, int]] = [
        (str(run.replay_path), len(run.result.mismatches)) for run in run_list
    ]
    total_mismatches = sum(count for _, count in mismatch_counts)
    worst_replay: str | None = None
    worst_count = 0
    if mismatch_counts:
        worst_replay, worst_count = max(mismatch_counts, key=lambda item: item[1])
    return BatchValidationSummary(
        total_replays=total,
        passed_count=passed,
        failed_count=failed,
        total_mismatches=total_mismatches,
        worst_replay=worst_replay,
        worst_mismatch_count=worst_count,
    )

"""Repro Lab report generation/export."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.engine_repro_lab.runner import ValidationRun

REPRO_REPORT_SCHEMA_VERSION = "tool.repro_lab_report.v1"


@dataclass(frozen=True)
class ReproReport:
    schema_version: str
    generated_at_utc: str
    replay_path: str
    fixed_step_seconds: float
    passed: bool
    total_ticks: int
    commands_applied: int
    checkpoint_count: int
    mismatch_count: int
    mismatches: list[dict[str, Any]]


def build_report(run: ValidationRun) -> ReproReport:
    result = run.result
    return ReproReport(
        schema_version=REPRO_REPORT_SCHEMA_VERSION,
        generated_at_utc=datetime.now(tz=UTC).isoformat(timespec="milliseconds"),
        replay_path=str(run.replay_path),
        fixed_step_seconds=float(run.config.fixed_step_seconds),
        passed=bool(result.passed),
        total_ticks=int(result.total_ticks),
        commands_applied=int(result.commands_applied),
        checkpoint_count=int(result.checkpoint_count),
        mismatch_count=len(result.mismatches),
        mismatches=[dict(mismatch) for mismatch in result.mismatches],
    )


def report_to_dict(report: ReproReport) -> dict[str, Any]:
    return {
        "schema_version": report.schema_version,
        "generated_at_utc": report.generated_at_utc,
        "replay_path": report.replay_path,
        "fixed_step_seconds": report.fixed_step_seconds,
        "passed": report.passed,
        "total_ticks": report.total_ticks,
        "commands_applied": report.commands_applied,
        "checkpoint_count": report.checkpoint_count,
        "mismatch_count": report.mismatch_count,
        "mismatches": list(report.mismatches),
    }


def export_report(report: ReproReport, path: Path) -> Path:
    payload = report_to_dict(report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path

"""Repro Lab validation runner."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.api.debug import ReplayValidationView, validate_replay_snapshot


@dataclass(frozen=True)
class ValidationConfig:
    fixed_step_seconds: float = 1.0 / 60.0


@dataclass(frozen=True)
class ValidationRun:
    replay_path: Path
    config: ValidationConfig
    result: ReplayValidationView


def load_replay_snapshot(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Replay payload must be a JSON object.")
    return payload


def run_validation(
    replay_snapshot: dict[str, Any],
    *,
    config: ValidationConfig,
    apply_command: Any,
    step: Any,
) -> ReplayValidationView:
    return validate_replay_snapshot(
        replay_snapshot,
        fixed_step_seconds=config.fixed_step_seconds,
        apply_command=apply_command,
        step=step,
    )


def run_validation_from_file(
    replay_path: Path,
    *,
    config: ValidationConfig,
    apply_command: Any,
    step: Any,
) -> ValidationRun:
    snapshot = load_replay_snapshot(replay_path)
    result = run_validation(
        snapshot,
        config=config,
        apply_command=apply_command,
        step=step,
    )
    return ValidationRun(replay_path=replay_path, config=config, result=result)

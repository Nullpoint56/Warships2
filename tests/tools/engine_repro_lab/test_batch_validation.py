from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.api.debug import ReplayValidationView
from tools.engine_repro_lab.batch import run_batch_validation, summarize_batch_runs
from tools.engine_repro_lab.runner import ValidationConfig, ValidationRun


def test_run_batch_validation_uses_factory_per_replay(monkeypatch) -> None:
    replay_paths = [Path("a.json"), Path("b.json"), Path("c.json")]
    calls: list[str] = []
    factory_calls = {"count": 0}

    def simulator_factory():
        factory_calls["count"] += 1

        def apply_command(_command):
            return None

        def step(_dt):
            return {"tick": factory_calls["count"]}

        return apply_command, step

    def fake_run_validation_from_file(replay_path, *, config, apply_command, step):
        _ = (config, apply_command, step)
        calls.append(str(replay_path))
        passed = replay_path.name != "b.json"
        mismatches = [] if passed else [{"tick": 3, "expected_hash": "x", "actual_hash": "y"}]
        return ValidationRun(
            replay_path=replay_path,
            config=ValidationConfig(),
            result=ReplayValidationView(
                schema_version="diag.replay_validation.v1",
                passed=passed,
                total_ticks=12,
                commands_applied=4,
                checkpoint_count=2,
                mismatches=mismatches,
            ),
        )

    monkeypatch.setattr(
        "tools.engine_repro_lab.batch.run_validation_from_file",
        fake_run_validation_from_file,
    )

    runs = run_batch_validation(
        replay_paths,
        config=ValidationConfig(),
        simulator_factory=simulator_factory,
    )

    assert len(runs) == 3
    assert calls == ["a.json", "b.json", "c.json"]
    assert factory_calls["count"] == 3


def test_summarize_batch_runs() -> None:
    runs = [
        ValidationRun(
            replay_path=Path("a.json"),
            config=ValidationConfig(),
            result=ReplayValidationView(
                schema_version="diag.replay_validation.v1",
                passed=True,
                total_ticks=10,
                commands_applied=3,
                checkpoint_count=1,
                mismatches=[],
            ),
        ),
        ValidationRun(
            replay_path=Path("b.json"),
            config=ValidationConfig(),
            result=ReplayValidationView(
                schema_version="diag.replay_validation.v1",
                passed=False,
                total_ticks=10,
                commands_applied=3,
                checkpoint_count=1,
                mismatches=[
                    {"tick": 2, "expected_hash": "a", "actual_hash": "b"},
                    {"tick": 3, "expected_hash": "c", "actual_hash": "d"},
                ],
            ),
        ),
    ]
    summary = summarize_batch_runs(runs)

    assert summary.total_replays == 2
    assert summary.passed_count == 1
    assert summary.failed_count == 1
    assert summary.total_mismatches == 2
    assert str(summary.worst_replay).endswith("b.json")
    assert summary.worst_mismatch_count == 2

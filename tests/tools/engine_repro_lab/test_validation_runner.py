from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.api.debug import ReplayValidationView
from tools.engine_repro_lab.runner import (
    ValidationConfig,
    load_replay_snapshot,
    run_validation_from_file,
)


def _sample_replay_payload() -> dict[str, object]:
    return {
        "schema_version": "diag.replay_session.v1",
        "manifest": {"seed": 7},
        "commands": [{"tick": 0, "command": {"type": "noop"}}],
        "state_hashes": [{"tick": 0, "hash": "abc"}],
    }


def test_load_replay_snapshot_reads_json_object(tmp_path: Path) -> None:
    path = tmp_path / "replay.json"
    path.write_text(json.dumps(_sample_replay_payload()), encoding="utf-8")

    payload = load_replay_snapshot(path)
    assert payload["schema_version"] == "diag.replay_session.v1"


def test_load_replay_snapshot_rejects_non_object(tmp_path: Path) -> None:
    path = tmp_path / "replay.json"
    path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    try:
        load_replay_snapshot(path)
    except ValueError as exc:
        assert "JSON object" in str(exc)
    else:
        assert False, "Expected ValueError for non-object replay payload."


def test_run_validation_from_file_uses_engine_api(tmp_path: Path, monkeypatch) -> None:
    replay_path = tmp_path / "replay.json"
    replay_path.write_text(json.dumps(_sample_replay_payload()), encoding="utf-8")

    calls: dict[str, object] = {}

    def fake_validate(
        replay_snapshot: dict[str, object],
        *,
        fixed_step_seconds: float,
        apply_command,
        step,
    ) -> ReplayValidationView:
        calls["snapshot"] = replay_snapshot
        calls["fixed_step_seconds"] = fixed_step_seconds
        calls["apply_command"] = apply_command
        calls["step"] = step
        return ReplayValidationView(
            schema_version="diag.replay_validation.v1",
            passed=True,
            total_ticks=10,
            commands_applied=3,
            checkpoint_count=2,
            mismatches=[],
        )

    monkeypatch.setattr("tools.engine_repro_lab.runner.validate_replay_snapshot", fake_validate)

    def apply_command(_cmd: object) -> None:
        return None

    def step(_dt: float) -> dict[str, int]:
        return {"tick": 0}

    run = run_validation_from_file(
        replay_path,
        config=ValidationConfig(fixed_step_seconds=1.0 / 120.0),
        apply_command=apply_command,
        step=step,
    )

    assert run.replay_path == replay_path
    assert run.result.passed is True
    assert calls["snapshot"] == _sample_replay_payload()
    assert float(calls["fixed_step_seconds"]) == 1.0 / 120.0

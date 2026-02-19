from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.api.debug import ReplayValidationView
from tools.engine_repro_lab.reporting import (
    REPRO_REPORT_SCHEMA_VERSION,
    build_report,
    export_report,
    report_to_dict,
)
from tools.engine_repro_lab.runner import ValidationConfig, ValidationRun


def test_report_build_and_schema_fields() -> None:
    run = ValidationRun(
        replay_path=Path("data/replay.json"),
        config=ValidationConfig(fixed_step_seconds=1.0 / 60.0),
        result=ReplayValidationView(
            schema_version="diag.replay_validation.v1",
            passed=False,
            total_ticks=42,
            commands_applied=12,
            checkpoint_count=3,
            mismatches=[
                {
                    "tick": 11,
                    "expected_hash": "aaaa",
                    "actual_hash": "bbbb",
                }
            ],
        ),
    )

    report = build_report(run)
    payload = report_to_dict(report)

    assert payload["schema_version"] == REPRO_REPORT_SCHEMA_VERSION
    assert str(payload["replay_path"]).replace("\\", "/") == "data/replay.json"
    assert payload["fixed_step_seconds"] == 1.0 / 60.0
    assert payload["passed"] is False
    assert payload["mismatch_count"] == 1
    assert payload["mismatches"][0]["tick"] == 11


def test_report_export_writes_json(tmp_path: Path) -> None:
    run = ValidationRun(
        replay_path=Path("replay.json"),
        config=ValidationConfig(),
        result=ReplayValidationView(
            schema_version="diag.replay_validation.v1",
            passed=True,
            total_ticks=1,
            commands_applied=1,
            checkpoint_count=0,
            mismatches=[],
        ),
    )
    report = build_report(run)
    out_path = tmp_path / "reports" / "repro_report.json"
    written = export_report(report, out_path)

    assert written == out_path
    content = json.loads(out_path.read_text(encoding="utf-8"))
    assert content["schema_version"] == REPRO_REPORT_SCHEMA_VERSION
    assert content["passed"] is True

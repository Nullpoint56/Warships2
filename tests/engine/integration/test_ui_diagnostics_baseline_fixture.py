from __future__ import annotations

import json
from pathlib import Path


def test_known_bad_ui_diag_fixture_is_valid_and_contains_anomalies() -> None:
    fixture = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "ui_diag_known_bad_resize_then_input.jsonl"
    )
    lines = fixture.read_text(encoding="utf-8").strip().splitlines()
    assert lines

    records = [json.loads(line) for line in lines]
    assert len(records) >= 2

    for record in records:
        assert "frame_seq" in record
        assert "reasons" in record
        assert "resize" in record
        assert "viewport" in record
        assert "buttons" in record
        assert "anomalies" in record

    anomalies = [
        item
        for record in records
        for item in record.get("anomalies", [])
        if isinstance(item, str)
    ]
    assert any(item.startswith("button_jitter:") for item in anomalies)
    assert any(item.startswith("button_ratio_spread:") for item in anomalies)

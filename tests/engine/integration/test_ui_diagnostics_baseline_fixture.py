from __future__ import annotations

import json
from pathlib import Path


def test_known_bad_ui_diag_fixture_has_valid_shape() -> None:
    fixture = (
        Path(__file__).resolve().parent / "fixtures" / "ui_diag_known_bad_resize_then_input.jsonl"
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

    anomalies = [record.get("anomalies", []) for record in records]
    assert all(isinstance(items, list) for items in anomalies)

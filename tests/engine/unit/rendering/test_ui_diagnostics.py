from __future__ import annotations

import json
from pathlib import Path

from engine.rendering.ui_diagnostics import UIDiagnostics, UIDiagnosticsConfig


def test_ui_diagnostics_detects_button_ratio_spread() -> None:
    diag = UIDiagnostics(
        UIDiagnosticsConfig(
            ui_trace_enabled=True,
            resize_trace_enabled=False,
            auto_dump_on_anomaly=False,
        )
    )
    diag.begin_frame()
    diag.note_viewport(width=1200, height=720, viewport_revision=1, sx=1.0, sy=1.0, ox=0.0, oy=0.0)
    diag.note_button_rect(
        "a",
        x=10.0,
        y=20.0,
        w=120.0,
        h=60.0,
        tx=10.0,
        ty=20.0,
        tw=120.0,
        th=60.0,
    )
    diag.note_button_text("a", text_size=20.0)
    diag.note_button_rect(
        "b",
        x=10.0,
        y=100.0,
        w=120.0,
        h=90.0,
        tx=10.0,
        ty=100.0,
        tw=120.0,
        th=90.0,
    )
    diag.note_button_text("b", text_size=20.0)
    diag.end_frame()

    last = diag.recent_frames()[-1]
    anomalies = last.get("anomalies")
    assert isinstance(anomalies, list)
    assert any(str(item).startswith("button_ratio_spread:") for item in anomalies)
    buttons = last.get("buttons")
    assert isinstance(buttons, dict)
    assert "source_rect" in buttons["a"]
    assert "rect" in buttons["a"]


def test_ui_diagnostics_detects_button_jitter_same_viewport_revision() -> None:
    diag = UIDiagnostics(
        UIDiagnosticsConfig(
            ui_trace_enabled=True,
            resize_trace_enabled=False,
            auto_dump_on_anomaly=False,
        )
    )

    diag.begin_frame()
    diag.note_viewport(width=1200, height=720, viewport_revision=7, sx=1.0, sy=1.0, ox=0.0, oy=0.0)
    diag.note_button_rect(
        "new_game",
        x=10.0,
        y=10.0,
        w=120.0,
        h=46.0,
        tx=10.0,
        ty=10.0,
        tw=120.0,
        th=46.0,
    )
    diag.note_button_text("new_game", text_size=18.0)
    diag.end_frame()

    diag.begin_frame()
    diag.note_viewport(width=1200, height=720, viewport_revision=7, sx=1.0, sy=1.0, ox=0.0, oy=0.0)
    diag.note_button_rect(
        "new_game",
        x=10.0,
        y=10.0,
        w=128.0,
        h=46.0,
        tx=10.0,
        ty=10.0,
        tw=128.0,
        th=46.0,
    )
    diag.note_button_text("new_game", text_size=18.0)
    diag.end_frame()

    last = diag.recent_frames()[-1]
    anomalies = last.get("anomalies")
    assert isinstance(anomalies, list)
    assert "button_jitter:new_game" in anomalies


def test_ui_diagnostics_dump_writes_jsonl(tmp_path: Path) -> None:
    diag = UIDiagnostics(
        UIDiagnosticsConfig(
            ui_trace_enabled=True,
            resize_trace_enabled=True,
            auto_dump_on_anomaly=False,
            dump_dir=str(tmp_path),
            dump_frame_count=10,
        )
    )
    diag.note_frame_reason("input:pointer")
    diag.note_resize_event(
        event_size=(1200.0, 720.0),
        logical_size=(1200.0, 720.0),
        physical_size=(1200, 720),
        applied_size=(1200, 720),
        viewport=(1.0, 1.0, 0.0, 0.0),
    )
    diag.begin_frame()
    diag.note_viewport(width=1200, height=720, viewport_revision=1, sx=1.0, sy=1.0, ox=0.0, oy=0.0)
    diag.end_frame()

    path = diag.dump_recent_frames()
    assert path is not None
    dump_path = Path(path)
    assert dump_path.exists()
    lines = dump_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["frame_seq"] == 1
    assert "resize" in payload
    assert "reasons" in payload
    assert "reason_events" in payload


def test_ui_diagnostics_tracks_reason_timestamps() -> None:
    diag = UIDiagnostics(
        UIDiagnosticsConfig(
            ui_trace_enabled=True,
            resize_trace_enabled=False,
            auto_dump_on_anomaly=False,
        )
    )
    diag.note_frame_reason("input:pointer:move")
    diag.begin_frame()
    diag.note_viewport(width=1200, height=720, viewport_revision=1, sx=1.0, sy=1.0, ox=0.0, oy=0.0)
    diag.end_frame()
    frame = diag.recent_frames()[-1]
    reason_events = frame.get("reason_events")
    assert isinstance(reason_events, list)
    assert reason_events
    assert reason_events[0]["reason"] == "input:pointer:move"

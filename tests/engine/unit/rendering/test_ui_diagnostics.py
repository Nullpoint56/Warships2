from __future__ import annotations

import json
from pathlib import Path

from engine.rendering.ui_diagnostics import UIDiagnostics, UIDiagnosticsConfig


def test_ui_diagnostics_records_button_geometry_without_soft_anomalies() -> None:
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
    assert anomalies == []
    buttons = last.get("buttons")
    assert isinstance(buttons, dict)
    assert "source_rect" in buttons["a"]
    assert "rect" in buttons["a"]


def test_ui_diagnostics_does_not_emit_button_jitter_anomaly() -> None:
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
    assert anomalies == []


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
        event_ts=10.0,
        size_applied_ts=10.001,
    )
    diag.begin_frame(frame_render_ts=10.010)
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
    assert "timing" in payload
    assert "reasons" in payload
    assert "reason_events" in payload
    resize = payload["resize"]
    assert isinstance(resize, dict)
    assert resize["event_to_apply_ms"] >= 0.0
    timing = payload["timing"]
    assert isinstance(timing, dict)
    assert timing["event_to_frame_ms"] >= 0.0
    assert timing["apply_to_frame_ms"] >= 0.0


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


def test_ui_diagnostics_records_filtered_primitives() -> None:
    diag = UIDiagnostics(
        UIDiagnosticsConfig(
            ui_trace_enabled=True,
            resize_trace_enabled=False,
            auto_dump_on_anomaly=False,
            primitive_trace_enabled=True,
            trace_key_prefixes=("ship:", "board:"),
        )
    )
    diag.begin_frame()
    diag.note_viewport(width=1200, height=720, viewport_revision=4, sx=1.0, sy=1.0, ox=0.0, oy=0.0)
    diag.note_primitive(
        primitive_type="rect",
        key="button:bg:new_game",
        source=(80.0, 28.0, 160.0, 50.0),
        transformed=(80.0, 28.0, 160.0, 50.0),
        z=1.0,
        viewport_revision=4,
    )
    diag.note_primitive(
        primitive_type="rect",
        key="ship:player:1:2",
        source=(100.0, 100.0, 42.0, 42.0),
        transformed=(110.0, 110.0, 42.0, 42.0),
        z=0.3,
        viewport_revision=4,
    )
    diag.note_primitive(
        primitive_type="rect",
        key="board:bg:player",
        source=(80.0, 150.0, 420.0, 420.0),
        transformed=(88.0, 165.0, 504.0, 462.0),
        z=0.1,
        viewport_revision=4,
    )
    diag.end_frame()
    frame = diag.recent_frames()[-1]
    primitives = frame.get("primitives")
    assert isinstance(primitives, list)
    keys = [item.get("key") for item in primitives if isinstance(item, dict)]
    assert "button:bg:new_game" not in keys
    assert "ship:player:1:2" in keys
    assert "board:bg:player" in keys
    anomalies = frame.get("anomalies")
    assert isinstance(anomalies, list)
    assert anomalies == []


def test_ui_diagnostics_does_not_emit_runtime_anomalies() -> None:
    diag = UIDiagnostics(
        UIDiagnosticsConfig(
            ui_trace_enabled=True,
            resize_trace_enabled=False,
            auto_dump_on_anomaly=False,
            primitive_trace_enabled=True,
        )
    )
    diag.begin_frame()
    diag.note_viewport(width=1200, height=720, viewport_revision=4, sx=1.0, sy=1.0, ox=0.0, oy=0.0)
    diag.note_primitive(
        primitive_type="rect",
        key="ui:one",
        source=(10.0, 10.0, 100.0, 100.0),
        transformed=(10.0, 10.0, 100.0, 100.0),
        z=0.1,
        viewport_revision=4,
    )
    diag.note_primitive(
        primitive_type="rect",
        key="ui:two",
        source=(10.0, 10.0, 100.0, 100.0),
        transformed=(10.0, 10.0, 100.0, 100.0),
        z=0.1,
        viewport_revision=5,
    )
    diag.end_frame()
    frame = diag.recent_frames()[-1]
    anomalies = frame.get("anomalies")
    assert isinstance(anomalies, list)
    assert anomalies == []


def test_ui_diagnostics_scope_decorator_captures_timing() -> None:
    diag = UIDiagnostics(
        UIDiagnosticsConfig(
            ui_trace_enabled=True,
            resize_trace_enabled=False,
            auto_dump_on_anomaly=False,
        )
    )
    diag.begin_frame()
    diag.note_viewport(width=1200, height=720, viewport_revision=1, sx=1.0, sy=1.0, ox=0.0, oy=0.0)

    @diag.scope_decorator("draw:board")
    def _draw_board() -> None:
        return None

    _draw_board()
    diag.end_frame()
    frame = diag.recent_frames()[-1]
    scopes = frame.get("scopes")
    assert isinstance(scopes, list)
    assert scopes
    assert scopes[0]["name"] == "draw:board"
